"""RBAC enforcement: FastAPI dependencies and decorators (T-035)."""

from __future__ import annotations

import logging
from functools import wraps
from typing import Callable, Optional

from fastapi import Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import get_async_session
from app.models.user import User
from app.services.rbac_service import RBACService

logger = logging.getLogger(__name__)


class PermissionChecker:
    """FastAPI dependency: raises 403 when the current user lacks a permission.

    Usage::

        @router.post("/tenders")
        async def create_tender(
            ...,
            _: User = Depends(PermissionChecker("tender:create")),
        ): ...
    """

    def __init__(self, permission: str):
        self.permission = permission

    async def __call__(
        self,
        request: Request,
        db: AsyncSession = Depends(get_async_session),
    ) -> User:
        user = getattr(request.state, "user", None)
        tenant_id = getattr(request.state, "tenant_id", None)
        if not user:
            raise HTTPException(status_code=401, detail="Not authenticated")
        uid = user.id if hasattr(user, "id") else (user.get("id") if isinstance(user, dict) else None)
        has_perm = await RBACService.user_has_permission(db, uid, tenant_id, self.permission)
        if not has_perm:
            logger.warning(
                "permission_denied user=%s tenant=%s permission=%s",
                uid, tenant_id, self.permission,
            )
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return user


class RoleChecker:
    """FastAPI dependency: raises 403 when the current user lacks a role.

    Usage::

        @router.delete("/tenants/{tenant_id}")
        async def delete_tenant(
            ...,
            _: User = Depends(RoleChecker("owner")),
        ): ...
    """

    def __init__(self, role_name: str):
        self.role_name = role_name

    async def __call__(
        self,
        request: Request,
        db: AsyncSession = Depends(get_async_session),
    ) -> User:
        from app.models.enterprise import TenantMember, Role
        from sqlalchemy import select

        user = getattr(request.state, "user", None)
        tenant_id = getattr(request.state, "tenant_id", None)
        if not user:
            raise HTTPException(status_code=401, detail="Not authenticated")
        uid = user.id if hasattr(user, "id") else (user.get("id") if isinstance(user, dict) else None)

        member = await db.scalar(
            select(TenantMember).where(
                (TenantMember.user_id == uid) & (TenantMember.tenant_id == tenant_id)
            )
        )
        if not member:
            raise HTTPException(status_code=404, detail="Not a member of this tenant")

        role = await db.scalar(select(Role).where(Role.id == member.role_id))
        if not role or role.name != self.role_name:
            logger.warning(
                "role_denied user=%s tenant=%s required=%s actual=%s",
                uid, tenant_id, self.role_name, role.name if role else None,
            )
            raise HTTPException(status_code=403, detail="Insufficient role")
        return user


async def get_current_user_with_tenant(
    request: Request,
    db: AsyncSession = Depends(get_async_session),
) -> tuple[User, Optional[str]]:
    """Extract current user and tenant_id from JWT + context.

    Returns: (user, tenant_id)
    """
    user = getattr(request.state, "user", None)
    tenant_id = getattr(request.state, "tenant_id", None)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user, tenant_id


def require_permission(permission: str) -> Callable:
    """Decorator: require a specific permission (resource:action).

    Example: @require_permission("tender:create")

    Raises:
    - 403 Forbidden: user lacks permission in their tenant
    - 404 Not Found: user not in the specified tenant (security: no info leak)
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            request: Optional[Request] = kwargs.get("request")
            db: Optional[AsyncSession] = kwargs.get("db")

            if not request or not db:
                raise HTTPException(status_code=500, detail="Missing request or db context")

            user = getattr(request.state, "user", None)
            tenant_id = getattr(request.state, "tenant_id", None)

            if not user or not tenant_id:
                raise HTTPException(status_code=401, detail="Not authenticated or no tenant context")

            has_perm = await RBACService.user_has_permission(
                db, user.id, tenant_id, permission
            )
            if not has_perm:
                logger.warning(
                    f"Permission denied: user={user.id} tenant={tenant_id} permission={permission}"
                )
                raise HTTPException(status_code=403, detail="Insufficient permissions")

            return await func(*args, **kwargs)

        return wrapper
    return decorator


def require_role(role_name: str) -> Callable:
    """Decorator: require a specific role (e.g., 'admin', 'owner').

    Example: @require_role("owner")
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            request: Optional[Request] = kwargs.get("request")
            db: Optional[AsyncSession] = kwargs.get("db")

            if not request or not db:
                raise HTTPException(status_code=500, detail="Missing request or db context")

            user = getattr(request.state, "user", None)
            tenant_id = getattr(request.state, "tenant_id", None)

            if not user or not tenant_id:
                raise HTTPException(status_code=401, detail="Not authenticated or no tenant context")

            from app.models.enterprise import TenantMember, Role
            from sqlalchemy import select

            member = await db.scalar(
                select(TenantMember).where(
                    (TenantMember.user_id == user.id) & (TenantMember.tenant_id == tenant_id)
                )
            )
            if not member:
                raise HTTPException(status_code=404, detail="Not a member of this tenant")

            role = await db.scalar(select(Role).where(Role.id == member.role_id))
            if not role or role.name != role_name:
                logger.warning(
                    f"Role denied: user={user.id} tenant={tenant_id} required={role_name} actual={role.name if role else None}"
                )
                raise HTTPException(status_code=403, detail="Insufficient role")

            return await func(*args, **kwargs)

        return wrapper
    return decorator
