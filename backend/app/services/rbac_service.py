"""RBAC service: role, permission, and tenant membership management (T-035)."""

from __future__ import annotations

import logging
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enterprise import Permission, Role, Tenant, TenantMember
from app.models.user import User

logger = logging.getLogger(__name__)

# Standard permission matrix: resource:action pairs
STANDARD_PERMISSIONS = [
    ("tender", "read"),
    ("tender", "create"),
    ("tender", "update"),
    ("tender", "delete"),
    ("boq", "read"),
    ("boq", "compare"),
    ("admin", "manage_users"),
    ("admin", "manage_roles"),
    ("admin", "view_audit"),
    ("reports", "generate"),
    ("settings", "read"),
    ("settings", "update"),
]

# Standard roles and their permissions
STANDARD_ROLES = {
    "owner": ["tender:read", "tender:create", "tender:update", "tender:delete",
              "boq:read", "boq:compare", "admin:manage_users", "admin:manage_roles",
              "admin:view_audit", "reports:generate", "settings:read", "settings:update"],
    "admin": ["tender:read", "tender:create", "tender:update", "boq:read", "boq:compare",
              "admin:manage_users", "admin:view_audit", "reports:generate", "settings:read", "settings:update"],
    "analyst": ["tender:read", "tender:create", "boq:read", "boq:compare", "reports:generate", "settings:read"],
    "viewer": ["tender:read", "boq:read", "settings:read"],
}


class RBACService:
    """Manage roles, permissions, and tenant memberships."""

    @staticmethod
    async def initialize_permissions(db: AsyncSession) -> None:
        """Create standard permissions if they don't exist."""
        for resource, action in STANDARD_PERMISSIONS:
            existing = await db.scalar(
                select(Permission).where(
                    (Permission.resource == resource) & (Permission.action == action)
                )
            )
            if not existing:
                perm = Permission(resource=resource, action=action)
                db.add(perm)
        await db.commit()

    @staticmethod
    async def initialize_system_roles(db: AsyncSession, tenant_id: Optional[str] = None) -> None:
        """Create standard roles if they don't exist."""
        for role_name, perms in STANDARD_ROLES.items():
            existing = await db.scalar(
                select(Role).where(
                    (Role.name == role_name) &
                    (Role.tenant_id == tenant_id) &
                    (Role.is_system == True)
                )
            )
            if not existing:
                perm_ids = []
                for perm_str in perms:
                    resource, action = perm_str.split(":")
                    perm = await db.scalar(
                        select(Permission).where(
                            (Permission.resource == resource) & (Permission.action == action)
                        )
                    )
                    if perm:
                        perm_ids.append(perm.id)

                role = Role(
                    name=role_name,
                    description=f"System role: {role_name}",
                    is_system=True,
                    tenant_id=tenant_id,
                    permission_ids=perm_ids,
                )
                db.add(role)
        await db.commit()

    @staticmethod
    async def provision_tenant(
        db: AsyncSession,
        tenant_name: str,
        tenant_slug: str,
        owner_id: str,
        plan: str = "free",
    ) -> Tenant:
        """Create a new tenant and assign owner."""
        tenant = Tenant(name=tenant_name, slug=tenant_slug, plan=plan)
        db.add(tenant)
        await db.flush()

        # Initialize system roles for this tenant
        await RBACService.initialize_system_roles(db, tenant_id=tenant.id)

        # Get owner role
        owner_role = await db.scalar(
            select(Role).where(
                (Role.tenant_id == tenant.id) & (Role.name == "owner") & (Role.is_system == True)
            )
        )

        if owner_role:
            member = TenantMember(
                user_id=owner_id,
                tenant_id=tenant.id,
                role_id=owner_role.id,
                is_owner=True,
            )
            db.add(member)

        await db.commit()
        return tenant

    @staticmethod
    async def add_tenant_member(
        db: AsyncSession,
        tenant_id: str,
        user_id: str,
        role_name: str,
    ) -> TenantMember:
        """Add a user to a tenant with a specific role."""
        role = await db.scalar(
            select(Role).where(
                (Role.tenant_id == tenant_id) & (Role.name == role_name)
            )
        )
        if not role:
            raise ValueError(f"Role '{role_name}' not found for tenant {tenant_id}")

        existing = await db.scalar(
            select(TenantMember).where(
                (TenantMember.user_id == user_id) & (TenantMember.tenant_id == tenant_id)
            )
        )
        if existing:
            existing.role_id = role.id
            await db.commit()
            return existing

        member = TenantMember(user_id=user_id, tenant_id=tenant_id, role_id=role.id)
        db.add(member)
        await db.commit()
        return member

    @staticmethod
    async def remove_tenant_member(
        db: AsyncSession,
        tenant_id: str,
        user_id: str,
    ) -> bool:
        """Remove a user from a tenant."""
        member = await db.scalar(
            select(TenantMember).where(
                (TenantMember.user_id == user_id) & (TenantMember.tenant_id == tenant_id)
            )
        )
        if not member:
            return False
        await db.delete(member)
        await db.commit()
        return True

    @staticmethod
    async def get_user_permissions(
        db: AsyncSession,
        user_id: str,
        tenant_id: str,
    ) -> List[str]:
        """Get all permissions for a user in a tenant (resource:action list)."""
        member = await db.scalar(
            select(TenantMember).where(
                (TenantMember.user_id == user_id) & (TenantMember.tenant_id == tenant_id)
            )
        )
        if not member:
            return []

        role = await db.scalar(select(Role).where(Role.id == member.role_id))
        if not role:
            return []

        # Fetch all permissions by ID
        perms = await db.execute(
            select(Permission).where(Permission.id.in_(role.permission_ids))
        )
        return [p.permission_string for p in perms.scalars()]

    @staticmethod
    async def user_has_permission(
        db: AsyncSession,
        user_id: str,
        tenant_id: str,
        permission: str,
    ) -> bool:
        """Check if user has a specific permission in a tenant."""
        permissions = await RBACService.get_user_permissions(db, user_id, tenant_id)
        return permission in permissions

    @staticmethod
    async def change_user_role(
        db: AsyncSession,
        tenant_id: str,
        user_id: str,
        new_role_name: str,
    ) -> TenantMember:
        """Change a user's role within a tenant."""
        role = await db.scalar(
            select(Role).where(
                (Role.tenant_id == tenant_id) & (Role.name == new_role_name)
            )
        )
        if not role:
            raise ValueError(f"Role '{new_role_name}' not found for tenant {tenant_id}")

        member = await db.scalar(
            select(TenantMember).where(
                (TenantMember.user_id == user_id) & (TenantMember.tenant_id == tenant_id)
            )
        )
        if not member:
            raise ValueError(f"User {user_id} not a member of tenant {tenant_id}")

        member.role_id = role.id
        await db.commit()
        return member

    @staticmethod
    async def get_tenant_members(
        db: AsyncSession,
        tenant_id: str,
    ) -> List[dict]:
        """Get all members of a tenant with their roles."""
        members = await db.execute(
            select(TenantMember, User, Role).where(
                TenantMember.tenant_id == tenant_id
            ).join(User, TenantMember.user_id == User.id).join(Role, TenantMember.role_id == Role.id)
        )
        result = []
        for member, user, role in members.all():
            result.append({
                "member_id": member.id,
                "user_id": user.id,
                "email": user.email,
                "full_name": user.full_name,
                "role": role.name,
                "is_owner": member.is_owner,
                "joined_at": member.joined_at.isoformat(),
            })
        return result
