"""T-035 (ENT-01a): RBAC tenant provisioning and role/permission enforcement tests."""

from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.main import app
from app.models.enterprise import Tenant, Role, TenantMember, Permission
from app.models.user import User
from app.db.database import get_async_session
from app.services.rbac_service import RBACService


@pytest.fixture()
def client():
    """FastAPI test client."""
    return TestClient(app)


@pytest.fixture()
async def superuser(db_session):
    """Create a superuser for tenant provisioning."""
    user = User(
        id=str(uuid.uuid4()),
        email=f"superuser-{uuid.uuid4().hex[:8]}@test.local",
        hashed_password="dummy",
        is_superuser=True,
    )
    db_session.add(user)
    await db_session.commit()
    return user


@pytest.fixture()
async def tenant_with_members(db_session, superuser):
    """Create a tenant with multiple members."""
    await RBACService.initialize_permissions(db_session)

    tenant = await RBACService.provision_tenant(
        db_session, "Test Tenant", "test-tenant", superuser.id, "free"
    )

    # Create additional users
    users = []
    for role_name in ["admin", "analyst", "viewer"]:
        user = User(
            id=str(uuid.uuid4()),
            email=f"user-{role_name}-{uuid.uuid4().hex[:4]}@test.local",
            hashed_password="dummy",
        )
        db_session.add(user)
        await db_session.flush()

        await RBACService.add_tenant_member(db_session, tenant.id, user.id, role_name)
        users.append((user, role_name))

    await db_session.commit()
    return tenant, superuser, users


class TestTenantProvisioning:
    """Tests for tenant provisioning."""

    @pytest.mark.asyncio
    async def test_provision_tenant_creates_system_roles(self, db_session, superuser):
        """Provision creates owner, admin, analyst, viewer roles."""
        await RBACService.initialize_permissions(db_session)

        tenant = await RBACService.provision_tenant(
            db_session, "My Tenant", "my-tenant", superuser.id, "pro"
        )

        assert tenant.name == "My Tenant"
        assert tenant.slug == "my-tenant"
        assert tenant.plan == "pro"

        # Check system roles exist
        roles = await db_session.execute(
            select(Role).where(
                (Role.tenant_id == tenant.id) & (Role.is_system == True)
            )
        )
        role_names = {r.name for r in roles.scalars()}
        assert role_names == {"owner", "admin", "analyst", "viewer"}

    @pytest.mark.asyncio
    async def test_owner_automatically_assigned(self, db_session, superuser):
        """Provisioning user automatically becomes owner."""
        await RBACService.initialize_permissions(db_session)

        tenant = await RBACService.provision_tenant(
            db_session, "Owner Test", "owner-test", superuser.id, "free"
        )

        member = await db_session.scalar(
            select(TenantMember).where(
                (TenantMember.tenant_id == tenant.id) & (TenantMember.user_id == superuser.id)
            )
        )
        assert member is not None
        assert member.is_owner is True

        role = await db_session.scalar(select(Role).where(Role.id == member.role_id))
        assert role.name == "owner"


class TestRBACMatrix:
    """Tests for permission enforcement."""

    @pytest.mark.asyncio
    async def test_owner_has_all_permissions(self, db_session, tenant_with_members):
        """Owner role has all standard permissions."""
        tenant, owner, members = tenant_with_members

        perms = await RBACService.get_user_permissions(db_session, owner.id, tenant.id)

        # Owner should have all permissions
        expected = {
            "tender:read", "tender:create", "tender:update", "tender:delete",
            "boq:read", "boq:compare",
            "admin:manage_users", "admin:manage_roles", "admin:view_audit",
            "reports:generate", "settings:read", "settings:update",
        }
        assert set(perms) == expected

    @pytest.mark.asyncio
    async def test_viewer_has_limited_permissions(self, db_session, tenant_with_members):
        """Viewer role has read-only permissions."""
        tenant, owner, members = tenant_with_members
        viewer_user, viewer_role = next((u, r) for u, r in members if r == "viewer")

        perms = await RBACService.get_user_permissions(db_session, viewer_user.id, tenant.id)

        expected = {"tender:read", "boq:read", "settings:read"}
        assert set(perms) == expected

    @pytest.mark.asyncio
    async def test_analyst_cannot_create_roles(self, db_session, tenant_with_members):
        """Analyst lacks admin:manage_roles permission."""
        tenant, owner, members = tenant_with_members
        analyst_user, analyst_role = next((u, r) for u, r in members if r == "analyst")

        can_manage = await RBACService.user_has_permission(
            db_session, analyst_user.id, tenant.id, "admin:manage_roles"
        )
        assert can_manage is False

    @pytest.mark.asyncio
    async def test_permission_check_returns_false_for_nonmember(self, db_session, superuser):
        """Non-members have no permissions."""
        await RBACService.initialize_permissions(db_session)

        tenant = await RBACService.provision_tenant(
            db_session, "Check Tenant", "check-tenant", superuser.id, "free"
        )

        other_user = User(
            id=str(uuid.uuid4()),
            email=f"other-{uuid.uuid4().hex[:4]}@test.local",
            hashed_password="dummy",
        )
        db_session.add(other_user)
        await db_session.commit()

        can_read = await RBACService.user_has_permission(
            db_session, other_user.id, tenant.id, "tender:read"
        )
        assert can_read is False


class TestRoleManagement:
    """Tests for role assignment and changes."""

    @pytest.mark.asyncio
    async def test_add_tenant_member(self, db_session, tenant_with_members):
        """Add user to tenant with specific role."""
        tenant, owner, members = tenant_with_members

        new_user = User(
            id=str(uuid.uuid4()),
            email=f"new-{uuid.uuid4().hex[:4]}@test.local",
            hashed_password="dummy",
        )
        db_session.add(new_user)
        await db_session.commit()

        member = await RBACService.add_tenant_member(
            db_session, tenant.id, new_user.id, "analyst"
        )

        assert member.user_id == new_user.id
        assert member.tenant_id == tenant.id

        role = await db_session.scalar(select(Role).where(Role.id == member.role_id))
        assert role.name == "analyst"

    @pytest.mark.asyncio
    async def test_change_user_role(self, db_session, tenant_with_members):
        """Change user's role within tenant."""
        tenant, owner, members = tenant_with_members
        analyst_user, _ = next((u, r) for u, r in members if r == "analyst")

        perms_before = await RBACService.get_user_permissions(db_session, analyst_user.id, tenant.id)
        assert "admin:manage_users" not in perms_before

        await RBACService.change_user_role(db_session, tenant.id, analyst_user.id, "admin")

        perms_after = await RBACService.get_user_permissions(db_session, analyst_user.id, tenant.id)
        assert "admin:manage_users" in perms_after

    @pytest.mark.asyncio
    async def test_remove_tenant_member(self, db_session, tenant_with_members):
        """Remove user from tenant."""
        tenant, owner, members = tenant_with_members
        viewer_user, _ = next((u, r) for u, r in members if r == "viewer")

        success = await RBACService.remove_tenant_member(db_session, tenant.id, viewer_user.id)
        assert success is True

        perms = await RBACService.get_user_permissions(db_session, viewer_user.id, tenant.id)
        assert len(perms) == 0


class TestCrossTenantIsolation:
    """Tests for isolation between tenants."""

    @pytest.mark.asyncio
    async def test_user_isolated_to_own_tenant(self, db_session, superuser):
        """User's permissions in one tenant don't leak to another."""
        await RBACService.initialize_permissions(db_session)

        tenant1 = await RBACService.provision_tenant(
            db_session, "Tenant 1", "tenant-1", superuser.id, "free"
        )
        tenant2 = await RBACService.provision_tenant(
            db_session, "Tenant 2", "tenant-2", superuser.id, "free"
        )

        user = User(
            id=str(uuid.uuid4()),
            email=f"shared-{uuid.uuid4().hex[:4]}@test.local",
            hashed_password="dummy",
        )
        db_session.add(user)
        await db_session.commit()

        # Add user as viewer to tenant1
        await RBACService.add_tenant_member(db_session, tenant1.id, user.id, "viewer")

        # User has no role in tenant2
        perms_t2 = await RBACService.get_user_permissions(db_session, user.id, tenant2.id)
        assert len(perms_t2) == 0

        # User has viewer perms in tenant1
        perms_t1 = await RBACService.get_user_permissions(db_session, user.id, tenant1.id)
        assert "tender:read" in perms_t1
        assert "admin:manage_users" not in perms_t1

    @pytest.mark.asyncio
    async def test_different_roles_in_different_tenants(self, db_session, superuser):
        """User can have different roles in different tenants."""
        await RBACService.initialize_permissions(db_session)

        tenant1 = await RBACService.provision_tenant(
            db_session, "Tenant A", "tenant-a", superuser.id, "free"
        )
        tenant2 = await RBACService.provision_tenant(
            db_session, "Tenant B", "tenant-b", superuser.id, "free"
        )

        user = User(
            id=str(uuid.uuid4()),
            email=f"multi-{uuid.uuid4().hex[:4]}@test.local",
            hashed_password="dummy",
        )
        db_session.add(user)
        await db_session.commit()

        # User is admin in tenant1, viewer in tenant2
        await RBACService.add_tenant_member(db_session, tenant1.id, user.id, "admin")
        await RBACService.add_tenant_member(db_session, tenant2.id, user.id, "viewer")

        perms_t1 = set(await RBACService.get_user_permissions(db_session, user.id, tenant1.id))
        perms_t2 = set(await RBACService.get_user_permissions(db_session, user.id, tenant2.id))

        # admin > viewer
        assert "admin:manage_users" in perms_t1
        assert "admin:manage_users" not in perms_t2
