"""Enterprise API v2: audit, retention, webhooks, RBAC, and platform capabilities (T-035)."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field

from app.core.security import get_current_user
from app.db.base import get_async_session
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
# get_db must be the plain async-generator dependency. database.get_async_session
# is an @asynccontextmanager, so FastAPI would inject the context-manager object
# (no .scalar/.execute) → 500. Alias to the base generator dependency instead.
get_db = get_async_session
from app.models.user import User
from app.models.enterprise import Tenant, TenantMember, Role
from app.services.audit_service import AuditService
from app.services.retention_service import RETENTION_TARGETS, RetentionService
from app.services.webhook_service import WebhookService
from app.services.rbac_service import RBACService
from app.services.quota_service import QuotaService
from app.core.tenant_rate_limiter import get_tenant_rate_limiter

router = APIRouter(prefix="/enterprise", tags=["enterprise-v2"])


def _uid(current_user) -> str | None:
    """Resolve a user id from request.state.user, which the auth middleware
    supplies as a dict (JWT claims) — not a User ORM object. Handles both."""
    if current_user is None:
        return None
    if isinstance(current_user, dict):
        return current_user.get("id") or current_user.get("user_id") or current_user.get("sub")
    return getattr(current_user, "id", None)


class AuditEventCreate(BaseModel):
    action: str = Field(..., min_length=2, max_length=120)
    resource_type: Optional[str] = Field(default=None, max_length=100)
    resource_id: Optional[str] = Field(default=None, max_length=120)
    status: str = Field(default="success", max_length=30)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class RetentionPolicyCreate(BaseModel):
    resource_type: str
    retention_days: int = Field(..., ge=1, le=3650)
    archive_before_delete: bool = True


class RetentionRunRequest(BaseModel):
    dry_run: bool = True
    limit_per_policy: int = Field(default=1000, ge=1, le=5000)


class WebhookPublishRequest(BaseModel):
    event_type: str = Field(..., min_length=2, max_length=100)
    payload: Dict[str, Any] = Field(default_factory=dict)
    event_id: Optional[str] = None


@router.get("/capabilities")
async def enterprise_capabilities():
    return {
        "api_versions": ["v1", "v2"],
        "features": {
            "audit_logging": True,
            "webhooks": True,
            "retention": True,
            "postgres_rls": True,
            "opentelemetry": "optional",
            "read_replicas": "configurable",
        },
        "retention_resource_types": sorted(RETENTION_TARGETS.keys()),
    }


@router.get("/audit-logs")
async def list_audit_logs(
    action: Optional[str] = None,
    resource_type: Optional[str] = None,
    limit: int = Query(default=100, ge=1, le=500),
    user: dict = Depends(get_current_user),
    db=Depends(get_async_session),
):
    rows = await AuditService(db).list_events(
        tenant_id=user.get("tenant_id"),
        action=action,
        resource_type=resource_type,
        limit=limit,
    )
    return {"success": True, "audit_logs": [row.to_dict() for row in rows]}


@router.post("/audit-logs")
async def create_audit_log(
    req: AuditEventCreate,
    user: dict = Depends(get_current_user),
    db=Depends(get_async_session),
):
    entry = await AuditService(db).log_event(
        tenant_id=user.get("tenant_id"),
        actor_id=user.get("id"),
        action=req.action,
        resource_type=req.resource_type,
        resource_id=req.resource_id,
        status=req.status,
        metadata=req.metadata,
    )
    await db.commit()
    return {"success": True, "audit_log": entry.to_dict()}


@router.get("/audit-logs/export")
async def export_audit_chain(
    limit: int = Query(default=1000, ge=1, le=5000),
    user: dict = Depends(get_current_user),
    db=Depends(get_async_session),
):
    """ENT-03: tamper-evident auditor export of the audit chain.

    Returns each entry with its hash-chain fields plus a verification summary,
    so an auditor can confirm integrity offline (see AuditService.export_chain).
    """
    result = await AuditService(db).export_chain(tenant_id=user.get("tenant_id"), limit=limit)
    return {"success": True, **result}


@router.get("/retention/policies")
async def list_retention_policies(user: dict = Depends(get_current_user), db=Depends(get_async_session)):
    rows = await RetentionService(db).list_policies(tenant_id=user.get("tenant_id"))
    return {
        "success": True,
        "policies": [
            {
                "id": row.id,
                "tenant_id": row.tenant_id,
                "resource_type": row.resource_type,
                "retention_days": row.retention_days,
                "archive_before_delete": row.archive_before_delete,
                "is_active": row.is_active,
                "created_at": row.created_at.isoformat() if row.created_at else None,
            }
            for row in rows
        ],
    }


@router.post("/retention/policies")
async def create_retention_policy(
    req: RetentionPolicyCreate,
    user: dict = Depends(get_current_user),
    db=Depends(get_async_session),
):
    try:
        policy = await RetentionService(db).create_policy(
            tenant_id=user.get("tenant_id"),
            resource_type=req.resource_type,
            retention_days=req.retention_days,
            archive_before_delete=req.archive_before_delete,
            created_by=user.get("id"),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await db.commit()
    return {"success": True, "policy_id": policy.id}


@router.post("/retention/run")
async def run_retention(
    req: RetentionRunRequest,
    user: dict = Depends(get_current_user),
    db=Depends(get_async_session),
):
    result = await RetentionService(db).run(
        tenant_id=user.get("tenant_id"),
        dry_run=req.dry_run,
        limit_per_policy=req.limit_per_policy,
    )
    if not req.dry_run:
        await db.commit()
    return {"success": True, **result}


@router.post("/webhooks/publish")
async def publish_webhook_event(
    req: WebhookPublishRequest,
    user: dict = Depends(get_current_user),
    db=Depends(get_async_session),
):
    result = await WebhookService(db).deliver(
        event_type=req.event_type,
        payload=req.payload,
        event_id=req.event_id,
        tenant_id=user.get("tenant_id"),
    )
    await db.commit()
    return {"success": True, **result}


# ── RBAC: Tenant Provisioning & Management (T-035) ────────────────────────

class TenantProvisionRequest(BaseModel):
    """Create a new tenant."""
    name: str
    slug: str
    plan: str = "free"


class TenantResponse(BaseModel):
    """Tenant info response."""
    id: str
    name: str
    slug: str
    plan: str
    is_active: bool
    created_at: Optional[str] = None
    config: Dict[str, Any] = Field(default_factory=dict)


class TenantMemberAddRequest(BaseModel):
    """Add a user to a tenant."""
    user_id: str
    role: str


class TenantMemberResponse(BaseModel):
    """Tenant member info."""
    member_id: str
    user_id: str
    email: str
    full_name: Optional[str]
    role: str
    is_owner: bool
    joined_at: str


class RoleResponse(BaseModel):
    """Role info."""
    id: str
    name: str
    description: Optional[str]
    permission_ids: List[str]
    is_system: bool


class PermissionResponse(BaseModel):
    """Permission info."""
    id: str
    resource: str
    action: str
    description: Optional[str]


class TenantUpdateRequest(BaseModel):
    """Update mutable tenant fields."""
    name: Optional[str] = None
    plan: Optional[str] = None
    is_active: Optional[bool] = None
    config: Optional[Dict[str, Any]] = None


@router.get("/tenants", response_model=List[TenantResponse])
async def list_tenants(
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
) -> List[TenantResponse]:
    """List all tenants (superuser only)."""
    current_user = await db.get(User, user.get("id")) if user.get("id") else None
    if not current_user or not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Only superusers can list all tenants")

    from sqlalchemy import select
    result = await db.execute(select(Tenant).order_by(
        Tenant.is_active.desc(),
        text("(COALESCE(config->>'client_rank', '999999'))::int"),
        Tenant.created_at.desc(),
    ))
    tenants = result.scalars().all()
    return [
        TenantResponse(
            id=t.id, name=t.name, slug=t.slug, plan=t.plan,
            is_active=t.is_active, created_at=t.created_at.isoformat() if t.created_at else None,
            config=t.config or {},
        )
        for t in tenants
    ]


@router.get("/current-tenant", response_model=TenantResponse)
async def get_current_tenant(
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
) -> TenantResponse:
    """Return the authenticated user's persisted enterprise tenant."""
    from sqlalchemy import select

    row = (
        await db.execute(
            select(Tenant)
            .join(TenantMember, TenantMember.tenant_id == Tenant.id)
            .where(TenantMember.user_id == user.get("id"))
            .order_by(TenantMember.is_owner.desc(), TenantMember.joined_at.asc())
            .limit(1)
        )
    ).scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="User has no enterprise tenant membership")

    return TenantResponse(
        id=row.id,
        name=row.name,
        slug=row.slug,
        plan=row.plan,
        is_active=row.is_active,
        created_at=row.created_at.isoformat() if row.created_at else None,
        config=row.config or {},
    )


@router.patch("/tenants/{tenant_id}", response_model=TenantResponse)
async def update_tenant(
    tenant_id: str,
    req: TenantUpdateRequest,
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
) -> TenantResponse:
    """Update tenant name, plan, or active status (superuser or tenant owner)."""
    from sqlalchemy import select
    from app.models.enterprise import TenantMember

    current_user = await db.get(User, user.get("id")) if user.get("id") else None
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    # Allow superuser OR tenant owner
    is_super = current_user.is_superuser
    if not is_super:
        member = await db.scalar(
            select(TenantMember).where(
                (TenantMember.user_id == current_user.id)
                & (TenantMember.tenant_id == tenant_id)
                & (TenantMember.is_owner == True)
            )
        )
        if not member:
            raise HTTPException(status_code=403, detail="Only tenant owners or superusers can update a tenant")

    tenant = await db.scalar(select(Tenant).where(Tenant.id == tenant_id))
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    if req.name is not None:
        tenant.name = req.name
    if req.plan is not None:
        if not is_super:
            raise HTTPException(status_code=403, detail="Only superusers can change the plan")
        tenant.plan = req.plan
    if req.is_active is not None:
        if not is_super:
            raise HTTPException(status_code=403, detail="Only superusers can deactivate tenants")
        tenant.is_active = req.is_active
    if req.config is not None:
        tenant.config = req.config

    await db.commit()
    await db.refresh(tenant)
    return TenantResponse(
        id=tenant.id, name=tenant.name, slug=tenant.slug, plan=tenant.plan,
        is_active=tenant.is_active, created_at=tenant.created_at.isoformat() if tenant.created_at else None,
    )


@router.post("/tenants", response_model=TenantResponse)
async def create_tenant(
    req: TenantProvisionRequest,
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
) -> TenantResponse:
    """Provision a new tenant (superuser only)."""
    current_user = await db.get(User, user.get("id")) if user.get("id") else None
    if not current_user or not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Only superusers can provision tenants")

    from sqlalchemy import select
    existing = await db.scalar(
        select(Tenant).where(Tenant.slug == req.slug)
    )
    if existing:
        raise HTTPException(status_code=409, detail="Tenant slug already exists")

    tenant = await RBACService.provision_tenant(
        db, req.name, req.slug, _uid(current_user), req.plan
    )

    return TenantResponse(
        id=tenant.id,
        name=tenant.name,
        slug=tenant.slug,
        plan=tenant.plan,
        is_active=tenant.is_active,
        created_at=tenant.created_at.isoformat() if tenant.created_at else None,
    )


@router.get("/tenants/{tenant_id}", response_model=TenantResponse)
async def get_tenant(
    tenant_id: str,
    request: Request,
    db=Depends(get_db),
) -> TenantResponse:
    """Get tenant info."""
    current_user: User = getattr(request.state, "user", None)
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    from app.models.enterprise import TenantMember
    from sqlalchemy import select

    member = await db.scalar(
        select(TenantMember).where(
            (TenantMember.user_id == _uid(current_user)) & (TenantMember.tenant_id == tenant_id)
        )
    )
    if not member:
        raise HTTPException(status_code=404, detail="Not a member of this tenant")

    tenant = await db.scalar(select(Tenant).where(Tenant.id == tenant_id))
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    return TenantResponse(
        id=tenant.id,
        name=tenant.name,
        slug=tenant.slug,
        plan=tenant.plan,
        is_active=tenant.is_active,
        created_at=tenant.created_at.isoformat() if tenant.created_at else None,
    )


@router.post("/tenants/{tenant_id}/members", response_model=TenantMemberResponse)
async def add_tenant_member(
    tenant_id: str,
    req: TenantMemberAddRequest,
    request: Request,
    db=Depends(get_db),
) -> TenantMemberResponse:
    """Add a user to a tenant with a specific role."""
    current_user: User = getattr(request.state, "user", None)
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    has_perm = await RBACService.user_has_permission(db, _uid(current_user), tenant_id, "admin:manage_users")
    if not has_perm:
        raise HTTPException(status_code=403, detail="Insufficient permissions to manage users")

    target_user = await db.get(User, req.user_id)
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")

    await RBACService.add_tenant_member(db, tenant_id, req.user_id, req.role)
    members = await RBACService.get_tenant_members(db, tenant_id)
    member_info = next(m for m in members if m["user_id"] == req.user_id)

    return TenantMemberResponse(**member_info)


@router.get("/tenants/{tenant_id}/members", response_model=List[TenantMemberResponse])
async def list_tenant_members(
    tenant_id: str,
    request: Request,
    db=Depends(get_db),
) -> List[TenantMemberResponse]:
    """List all members of a tenant."""
    current_user: User = getattr(request.state, "user", None)
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    from app.models.enterprise import TenantMember
    from sqlalchemy import select

    member = await db.scalar(
        select(TenantMember).where(
            (TenantMember.user_id == _uid(current_user)) & (TenantMember.tenant_id == tenant_id)
        )
    )
    if not member:
        raise HTTPException(status_code=404, detail="Not a member of this tenant")

    members = await RBACService.get_tenant_members(db, tenant_id)
    return [TenantMemberResponse(**m) for m in members]


@router.put("/tenants/{tenant_id}/members/{user_id}/role")
async def change_user_role(
    tenant_id: str,
    user_id: str,
    new_role: str,
    request: Request,
    db=Depends(get_db),
) -> TenantMemberResponse:
    """Change a user's role within a tenant."""
    current_user: User = getattr(request.state, "user", None)
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    has_perm = await RBACService.user_has_permission(db, _uid(current_user), tenant_id, "admin:manage_roles")
    if not has_perm:
        raise HTTPException(status_code=403, detail="Insufficient permissions to manage roles")

    await RBACService.change_user_role(db, tenant_id, user_id, new_role)
    members = await RBACService.get_tenant_members(db, tenant_id)
    member_info = next(m for m in members if m["user_id"] == user_id)

    return TenantMemberResponse(**member_info)


@router.delete("/tenants/{tenant_id}/members/{user_id}")
async def remove_tenant_member(
    tenant_id: str,
    user_id: str,
    request: Request,
    db=Depends(get_db),
) -> dict:
    """Remove a user from a tenant."""
    current_user: User = getattr(request.state, "user", None)
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    has_perm = await RBACService.user_has_permission(db, _uid(current_user), tenant_id, "admin:manage_users")
    if not has_perm:
        raise HTTPException(status_code=403, detail="Insufficient permissions to manage users")

    success = await RBACService.remove_tenant_member(db, tenant_id, user_id)
    if not success:
        raise HTTPException(status_code=404, detail="User not a member of this tenant")

    return {"success": True, "message": "User removed from tenant"}


@router.get("/roles", response_model=List[RoleResponse])
async def list_roles(
    tenant_id: str,
    request: Request,
    db=Depends(get_db),
) -> List[RoleResponse]:
    """List available roles for a tenant."""
    current_user: User = getattr(request.state, "user", None)
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    from app.models.enterprise import TenantMember
    from sqlalchemy import select

    member = await db.scalar(
        select(TenantMember).where(
            (TenantMember.user_id == _uid(current_user)) & (TenantMember.tenant_id == tenant_id)
        )
    )
    if not member:
        raise HTTPException(status_code=404, detail="Not a member of this tenant")

    roles = await db.execute(
        select(Role).where((Role.tenant_id == tenant_id) | (Role.is_system == True))
    )
    return [
        RoleResponse(
            id=r.id,
            name=r.name,
            description=r.description,
            permission_ids=r.permission_ids,
            is_system=r.is_system,
        )
        for r in roles.scalars()
    ]


@router.get("/permissions", response_model=List[PermissionResponse])
async def list_permissions(
    request: Request,
    db=Depends(get_db),
) -> List[PermissionResponse]:
    """List all available permissions."""
    current_user: User = getattr(request.state, "user", None)
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    from app.models.enterprise import Permission
    from sqlalchemy import select

    perms = await db.execute(select(Permission))
    return [
        PermissionResponse(
            id=p.id,
            resource=p.resource,
            action=p.action,
            description=p.description,
        )
        for p in perms.scalars()
    ]


# ── Quotas & Rate Limiting (T-036) ────────────────────────────────────────

@router.get("/tenants/{tenant_id}/quota")
async def get_tenant_quota(
    tenant_id: str,
    request: Request,
    db=Depends(get_db),
) -> dict:
    """Get current tender quota for tenant."""
    current_user: User = getattr(request.state, "user", None)
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    from app.models.enterprise import TenantMember
    from sqlalchemy import select

    # Verify user is member
    member = await db.scalar(
        select(TenantMember).where(
            (TenantMember.user_id == _uid(current_user)) & (TenantMember.tenant_id == tenant_id)
        )
    )
    if not member:
        raise HTTPException(status_code=404, detail="Not a member of this tenant")

    quota = await QuotaService.get_quota_summary(db, tenant_id)
    return quota


@router.get("/tenants/{tenant_id}/rate-limit")
async def get_rate_limit_status(
    tenant_id: str,
    request: Request,
    endpoint: str = Query(...),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get current rate limit status for tenant/endpoint."""
    current_user: User = getattr(request.state, "user", None)
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    from app.models.enterprise import TenantMember
    from sqlalchemy import select

    # Verify user is member
    member = await db.scalar(
        select(TenantMember).where(
            (TenantMember.user_id == _uid(current_user)) & (TenantMember.tenant_id == tenant_id)
        )
    )
    if not member:
        raise HTTPException(status_code=404, detail="Not a member of this tenant")

    # Get tenant's plan to determine rate limits
    from app.models.subscription import ClientSubscription

    sub = await db.scalar(
        select(ClientSubscription).where(ClientSubscription.tenant_id == tenant_id)
    )
    plan = sub.plan.value if sub else "free"

    limiter = get_tenant_rate_limiter()
    status = await limiter.get_status(tenant_id, endpoint, plan)
    return status


@router.get("/tenants/{tenant_id}/usage")
async def get_tenant_usage(
    tenant_id: str,
    request: Request,
    db=Depends(get_db),
) -> dict:
    """Get detailed usage metrics for tenant (all quotas + rate limits)."""
    current_user: User = getattr(request.state, "user", None)
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    from app.models.enterprise import TenantMember
    from sqlalchemy import select

    # Verify user is member
    member = await db.scalar(
        select(TenantMember).where(
            (TenantMember.user_id == _uid(current_user)) & (TenantMember.tenant_id == tenant_id)
        )
    )
    if not member:
        raise HTTPException(status_code=404, detail="Not a member of this tenant")

    # Get all metrics
    quota = await QuotaService.get_quota_summary(db, tenant_id)
    limiter = get_tenant_rate_limiter()

    # Get rate limits for common endpoints
    endpoints = ["/api/tenders", "/api/boq", "/api/agents"]
    rate_limits = {}
    for ep in endpoints:
        status = await limiter.get_status(tenant_id, ep, quota["plan"])
        rate_limits[ep] = status

    return {
        "tenant_id": tenant_id,
        "plan": quota["plan"],
        "quota": quota["tender_quota"],
        "rate_limits": rate_limits,
        "warning_threshold": quota["warning_threshold"],
        "warning_active": quota["warning_active"],
        "status": quota["status"],
    }
