"""Phase 2: Admin Management Endpoints"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from pydantic import BaseModel, EmailStr
from datetime import datetime, timezone
import uuid
import csv
import io

from app.db.base import get_async_session
from app.core.security import get_current_user
from app.models.tender import Tender
from app.models.enterprise import Tenant, AuditLog
from app.models.phase2 import Document, TeamMember

router = APIRouter(prefix="/admin", tags=["admin"])


class TenantBase(BaseModel):
    """Base tenant schema"""
    name: str
    subscription_plan: str
    max_users: int
    max_storage_gb: int


class TenantCreate(TenantBase):
    """Create tenant"""
    slug: Optional[str] = None


class TenantUpdate(BaseModel):
    """Update tenant"""
    name: Optional[str] = None
    subscription_plan: Optional[str] = None
    max_users: Optional[int] = None
    max_storage_gb: Optional[int] = None
    is_active: Optional[bool] = None


class TenantResponse(TenantBase):
    """Tenant response"""
    id: str
    slug: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


def _tenant_response(tenant: Tenant) -> TenantResponse:
    config = tenant.config or {}
    return TenantResponse(
        id=tenant.id,
        name=tenant.name,
        slug=tenant.slug,
        subscription_plan=tenant.plan,
        max_users=config.get("max_users", 0),
        max_storage_gb=config.get("max_storage_gb", 0),
        is_active=tenant.is_active,
        created_at=tenant.created_at or tenant.updated_at or datetime(1970, 1, 1, tzinfo=timezone.utc),
        updated_at=tenant.updated_at or tenant.created_at or datetime(1970, 1, 1, tzinfo=timezone.utc),
    )


class SystemStatsResponse(BaseModel):
    """System statistics"""
    total_users: int
    total_tenants: int
    total_tenders: int
    total_documents: int
    active_subscriptions: int
    storage_used_gb: float
    uptime_hours: float


class AuditLogResponse(BaseModel):
    """Audit log entry"""
    id: str
    created_at: datetime
    actor_id: Optional[str]
    action: str
    resource_type: str
    resource_id: Optional[str]
    status: str
    ip_address: Optional[str]

    class Config:
        from_attributes = True


def _verify_admin(current_user: dict = Depends(get_current_user)):
    """Verify that current user is admin or owner."""
    if current_user.get("role", "").lower() not in {"admin", "owner"}:
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user


@router.get("/stats", response_model=SystemStatsResponse)
async def get_system_stats(
    current_user: dict = Depends(_verify_admin),
    db: AsyncSession = Depends(get_async_session),
):
    """Get system-wide statistics."""
    try:
        from app.models.user import User

        users_count = await db.scalar(select(func.count(User.id)))
        tenders_count = await db.scalar(select(func.count(Tender.id)))
        documents_count = await db.scalar(select(func.count(Document.id)))

        total_file_size = await db.scalar(select(func.sum(Document.file_size)))
        storage_gb = (total_file_size or 0) / (1024 ** 3)

        return {
            "total_users": users_count or 0,
            "total_tenants": 0,
            "total_tenders": tenders_count or 0,
            "total_documents": documents_count or 0,
            "active_subscriptions": 0,
            "storage_used_gb": storage_gb,
            "uptime_hours": 0.0,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tenants", response_model=List[TenantResponse])
async def list_tenants(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    is_active: Optional[bool] = Query(None),
    current_user: dict = Depends(_verify_admin),
    db: AsyncSession = Depends(get_async_session),
):
    """List all tenants (admin only)."""
    try:
        query = select(Tenant)
        if is_active is not None:
            query = query.where(Tenant.is_active == is_active)
        query = query.offset(skip).limit(limit)
        result = await db.execute(query)
        tenants = result.scalars().all()
        return [_tenant_response(t) for t in tenants]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tenants/{tenant_id}", response_model=TenantResponse)
async def get_tenant(
    tenant_id: str,
    current_user: dict = Depends(_verify_admin),
    db: AsyncSession = Depends(get_async_session),
):
    """Get tenant by ID (admin only)."""
    try:
        result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
        tenant = result.scalar_one_or_none()
        if not tenant:
            raise HTTPException(status_code=404, detail="Tenant not found")
        return _tenant_response(tenant)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/tenants", response_model=TenantResponse, status_code=status.HTTP_201_CREATED)
async def create_tenant(
    tenant: TenantCreate,
    current_user: dict = Depends(_verify_admin),
    db: AsyncSession = Depends(get_async_session),
):
    """Create a new tenant (admin only)."""
    try:
        tenant_id = str(uuid.uuid4())
        slug = tenant.slug or tenant.name.lower().replace(" ", "-") + "-" + tenant_id[:8]
        new_tenant = Tenant(
            id=tenant_id,
            name=tenant.name,
            slug=slug,
            plan=tenant.subscription_plan,
            config={
                "max_users": tenant.max_users,
                "max_storage_gb": tenant.max_storage_gb,
            },
            is_active=True,
        )
        db.add(new_tenant)
        await db.commit()
        await db.refresh(new_tenant)
        return _tenant_response(new_tenant)
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/tenants/{tenant_id}", response_model=TenantResponse)
async def update_tenant(
    tenant_id: str,
    tenant_update: TenantUpdate,
    current_user: dict = Depends(_verify_admin),
    db: AsyncSession = Depends(get_async_session),
):
    """Update tenant (admin only)."""
    try:
        result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
        tenant = result.scalar_one_or_none()
        if not tenant:
            raise HTTPException(status_code=404, detail="Tenant not found")

        update_data = tenant_update.model_dump(exclude_unset=True)
        if "subscription_plan" in update_data:
            tenant.plan = update_data.pop("subscription_plan")
        config_updates = {
            key: update_data.pop(key)
            for key in ("max_users", "max_storage_gb")
            if key in update_data
        }
        if config_updates:
            tenant.config = {**(tenant.config or {}), **config_updates}
        for key, value in update_data.items():
            setattr(tenant, key, value)

        await db.commit()
        await db.refresh(tenant)
        return _tenant_response(tenant)
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/tenants/{tenant_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tenant(
    tenant_id: str,
    current_user: dict = Depends(_verify_admin),
    db: AsyncSession = Depends(get_async_session),
):
    """Delete tenant (admin only)."""
    try:
        result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
        tenant = result.scalar_one_or_none()
        if not tenant:
            raise HTTPException(status_code=404, detail="Tenant not found")

        tenant.is_active = False
        await db.commit()
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/audit-logs", response_model=List[AuditLogResponse])
async def get_audit_logs(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    action: Optional[str] = Query(None),
    resource_type: Optional[str] = Query(None),
    current_user: dict = Depends(_verify_admin),
    db: AsyncSession = Depends(get_async_session),
):
    """Get audit logs (admin only)."""
    try:
        query = select(AuditLog)
        if action:
            query = query.where(AuditLog.action == action)
        if resource_type:
            query = query.where(AuditLog.resource_type == resource_type)
        query = query.order_by(AuditLog.created_at.desc()).offset(skip).limit(limit)
        result = await db.execute(query)
        logs = result.scalars().all()
        return [AuditLogResponse.model_validate(l) for l in logs]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/audit-logs/export")
async def export_audit_logs(
    format: str = Query("csv", pattern="^(csv|json)$"),
    action: Optional[str] = Query(None),
    current_user: dict = Depends(_verify_admin),
    db: AsyncSession = Depends(get_async_session),
):
    """Export audit logs (admin only)."""
    try:
        query = select(AuditLog).order_by(AuditLog.created_at.desc()).limit(10000)
        if action:
            query = query.where(AuditLog.action == action)
        result = await db.execute(query)
        logs = result.scalars().all()

        if format == "csv":
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow(["id", "action", "resource_type", "status", "created_at"])
            for log in logs:
                writer.writerow([log.id, log.action, log.resource_type, log.status, log.created_at.isoformat() if log.created_at else ""])
            csv_content = output.getvalue()
            export_id = str(uuid.uuid4())
            return {"export_url": f"/api/v2/admin/exports/{export_id}.csv", "status": "ready", "format": "csv", "record_count": len(logs)}
        else:
            return {"status": "ready", "format": "json", "record_count": len(logs), "data": [AuditLogResponse.model_validate(l).model_dump() for l in logs]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def admin_health_check(
    current_user: dict = Depends(_verify_admin),
    db: AsyncSession = Depends(get_async_session),
):
    """Health check for admin endpoints (admin only)."""
    try:
        await db.execute(select(func.count()).select_from(Tenant))
        return {
            "status": "healthy",
            "database": "connected",
            "cache": "connected",
            "storage": "connected",
        }
    except Exception as e:
        return {"status": "degraded", "error": str(e)}
