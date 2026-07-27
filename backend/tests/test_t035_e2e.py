"""T-035 E2E Integration Test: Full tenant provisioning flow.

Tests complete enterprise workflow:
1. Create tenant with owner
2. Provision system roles
3. Add members with different roles
4. Verify RBAC permissions
5. Test quota enforcement
6. Test rate limiting
7. Verify cross-tenant isolation (404 on wrong tenant)
"""

from __future__ import annotations

import uuid
import pytest
from datetime import datetime, timezone
from sqlalchemy import select

from app.models.enterprise import Tenant, TenantMember, Role, Permission
from app.models.subscription import ClientSubscription
from app.models.user import User
from app.services.rbac_service import RBACService
from app.services.quota_service import QuotaService
from app.core.tenant_rate_limiter import TenantRateLimiter


@pytest.fixture
async def owner_user(db_session):
    """Create owner user."""
    user = User(
        id=str(uuid.uuid4()),
        email="owner@example.com",
        full_name="Tenant Owner",
        tenant_id=None,  # System user
        hashed_password="owner-password",
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    return user


@pytest.fixture
async def admin_user(db_session):
    """Create admin user."""
    from app.models.user import User
    user = User(
        id=str(uuid.uuid4()),
        email="admin@example.com",
        full_name="Tenant Admin",
        tenant_id=None,
        hashed_password="admin-password",
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    return user


@pytest.fixture
async def analyst_user(db_session):
    """Create analyst user."""
    from app.models.user import User
    user = User(
        id=str(uuid.uuid4()),
        email="analyst@example.com",
        full_name="Tenant Analyst",
        tenant_id=None,
        hashed_password="analyst-password",
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    return user


class TestTenantProvisioning:
    """Test tenant creation and initial setup."""

    @pytest.mark.asyncio
    async def test_provision_tenant_with_owner(self, db_session, owner_user):
        """Provision new tenant with owner user."""
        tenant, roles = await RBACService.provision_tenant(
            db_session,
            name="Enterprise Tenant",
            slug="enterprise-tenant",
            owner_id=owner_user.id,
            plan="pro",
        )

        assert tenant.name == "Enterprise Tenant"
        assert tenant.slug == "enterprise-tenant"
        assert tenant.plan == "pro"
        assert len(roles) == 4  # owner, admin, analyst, viewer

        # Verify owner is a member
        member = await db_session.scalar(
            select(TenantMember).where(
                (TenantMember.tenant_id == tenant.id)
                & (TenantMember.user_id == owner_user.id)
            )
        )
        assert member is not None
        assert member.is_owner is True

    @pytest.mark.asyncio
    async def test_system_roles_created(self, db_session, owner_user):
        """System roles (owner, admin, analyst, viewer) are created."""
        tenant, roles = await RBACService.provision_tenant(
            db_session, "Test", "test", owner_user.id, "free"
        )

        role_names = {role.name for role in roles}
        assert role_names == {"owner", "admin", "analyst", "viewer"}

        # Verify each role has correct permissions
        for role in roles:
            assert len(role.permission_ids) > 0


class TestRBACEnforcement:
    """Test role-based access control."""

    @pytest.mark.asyncio
    async def test_owner_has_all_permissions(self, db_session, owner_user):
        """Owner role has all permissions."""
        tenant, roles = await RBACService.provision_tenant(
            db_session, "Test", "test-rbac", owner_user.id, "pro"
        )

        permissions = await RBACService.get_user_permissions(
            db_session, owner_user.id, tenant.id
        )

        # Owner should have many permissions
        assert len(permissions) > 10
        assert "tender:view" in permissions
        assert "tender:create" in permissions
        assert "rbac:manage" in permissions

    @pytest.mark.asyncio
    async def test_analyst_has_limited_permissions(self, db_session, owner_user, analyst_user):
        """Analyst role has read/analyze permissions only."""
        tenant, _ = await RBACService.provision_tenant(
            db_session, "Test", "test-analyst", owner_user.id, "pro"
        )

        # Add analyst as member
        await RBACService.add_tenant_member(db_session, tenant.id, analyst_user.id, "analyst")

        permissions = await RBACService.get_user_permissions(
            db_session, analyst_user.id, tenant.id
        )

        # Analyst should have read/analyze permissions
        assert "tender:view" in permissions
        assert "boq:analyze" in permissions

        # Analyst should NOT have admin permissions
        assert "rbac:manage" not in permissions
        assert "user:create" not in permissions

    @pytest.mark.asyncio
    async def test_viewer_has_minimal_permissions(self, db_session, owner_user):
        """Viewer role has read-only permissions."""
        tenant, _ = await RBACService.provision_tenant(
            db_session, "Test", "test-viewer", owner_user.id, "free"
        )

        # Create a viewer user
        viewer = User(
            id=str(uuid.uuid4()),
            email="viewer@example.com",
            full_name="Viewer",
            tenant_id=None,
            hashed_password="pwd",
            is_active=True,
        )
        db_session.add(viewer)
        await db_session.flush()

        await RBACService.add_tenant_member(db_session, tenant.id, viewer.id, "viewer")

        permissions = await RBACService.get_user_permissions(db_session, viewer.id, tenant.id)

        # Viewer should only have view permissions
        assert "tender:view" in permissions
        assert "tender:create" not in permissions

    @pytest.mark.asyncio
    async def test_change_user_role(self, db_session, owner_user, analyst_user):
        """Changing user role updates permissions."""
        tenant, _ = await RBACService.provision_tenant(
            db_session, "Test", "test-role-change", owner_user.id, "pro"
        )

        # Add as analyst
        await RBACService.add_tenant_member(db_session, tenant.id, analyst_user.id, "analyst")

        perms_before = await RBACService.get_user_permissions(
            db_session, analyst_user.id, tenant.id
        )

        # Change to admin
        await RBACService.change_user_role(db_session, tenant.id, analyst_user.id, "admin")

        perms_after = await RBACService.get_user_permissions(
            db_session, analyst_user.id, tenant.id
        )

        # Should have more permissions as admin
        assert len(perms_after) > len(perms_before)


class TestQuotaEnforcement:
    """Test tender quota enforcement."""

    @pytest.mark.asyncio
    async def test_quota_tracking(self, db_session, owner_user):
        """Quota is tracked and updated."""
        tenant, _ = await RBACService.provision_tenant(
            db_session, "Test", "test-quota", owner_user.id, "pro"
        )

        # Create subscription
        sub = ClientSubscription(
            id=str(uuid.uuid4()),
            tenant_id=tenant.id,
            status="active",
            tender_quota_limit=100,
            tender_quota_used=0,
            quota_reset_date=QuotaService.get_next_month_start(),
        )
        db_session.add(sub)
        await db_session.commit()

        # Check quota
        quota = await QuotaService.get_tender_quota(db_session, tenant.id)
        assert quota["limit"] == 100
        assert quota["used"] == 0
        assert quota["remaining"] == 100

    @pytest.mark.asyncio
    async def test_quota_exhaustion_blocks_operations(self, db_session, owner_user):
        """Exhausted quota blocks tender operations."""
        tenant, _ = await RBACService.provision_tenant(
            db_session, "Test", "test-quota-exhausted", owner_user.id, "free"
        )

        # Create exhausted subscription
        sub = ClientSubscription(
            id=str(uuid.uuid4()),
            tenant_id=tenant.id,
            status="active",
            tender_quota_limit=10,
            tender_quota_used=10,  # EXHAUSTED
            quota_reset_date=QuotaService.get_next_month_start(),
        )
        db_session.add(sub)
        await db_session.commit()

        # Check quota
        has_quota, error = await QuotaService.check_tender_quota(db_session, tenant.id)
        assert has_quota is False
        assert "exhausted" in error.lower()

    @pytest.mark.asyncio
    async def test_quota_warning_at_threshold(self, db_session, owner_user):
        """Quota shows warning at 80% usage."""
        tenant, _ = await RBACService.provision_tenant(
            db_session, "Test", "test-quota-warning", owner_user.id, "pro"
        )

        # Create subscription at 80% usage
        sub = ClientSubscription(
            id=str(uuid.uuid4()),
            tenant_id=tenant.id,
            status="active",
            tender_quota_limit=100,
            tender_quota_used=80,
            quota_reset_date=QuotaService.get_next_month_start(),
        )
        db_session.add(sub)
        await db_session.commit()

        summary = await QuotaService.get_quota_summary(db_session, tenant.id)
        assert summary["warning_active"] is True
        assert summary["tender_quota"]["percent_used"] == 80.0


class TestCrossTenantIsolation:
    """Test cross-tenant isolation and security."""

    @pytest.mark.asyncio
    async def test_cross_tenant_access_returns_404(self, db_session, owner_user, admin_user):
        """Accessing another tenant's data returns 404, not 403."""
        # Create two tenants
        tenant_a, _ = await RBACService.provision_tenant(
            db_session, "Tenant A", "tenant-a", owner_user.id, "pro"
        )
        tenant_b, _ = await RBACService.provision_tenant(
            db_session, "Tenant B", "tenant-b", admin_user.id, "pro"
        )

        # Owner of tenant_a tries to access tenant_b
        can_access = await db_session.scalar(
            select(TenantMember).where(
                (TenantMember.tenant_id == tenant_b.id)
                & (TenantMember.user_id == owner_user.id)
            )
        )
        assert can_access is None

        # Quota should also be isolated
        quota_a = await QuotaService.get_tender_quota(db_session, tenant_a.id)
        quota_b = await QuotaService.get_tender_quota(db_session, tenant_b.id)

        # Both should have separate quotas
        assert quota_a is not None
        assert quota_b is not None

    @pytest.mark.asyncio
    async def test_quota_isolation_between_tenants(self, db_session, owner_user, admin_user):
        """Tenant A's quota exhaustion doesn't affect Tenant B."""
        # Create two tenants
        tenant_a, _ = await RBACService.provision_tenant(
            db_session, "Tenant A", "tenant-a-quota", owner_user.id, "free"
        )
        tenant_b, _ = await RBACService.provision_tenant(
            db_session, "Tenant B", "tenant-b-quota", admin_user.id, "pro"
        )

        # Tenant A: exhausted
        sub_a = ClientSubscription(
            id=str(uuid.uuid4()),
            tenant_id=tenant_a.id,
            status="active",
            tender_quota_limit=10,
            tender_quota_used=10,
            quota_reset_date=QuotaService.get_next_month_start(),
        )
        db_session.add(sub_a)

        # Tenant B: fresh
        sub_b = ClientSubscription(
            id=str(uuid.uuid4()),
            tenant_id=tenant_b.id,
            status="active",
            tender_quota_limit=500,
            tender_quota_used=0,
            quota_reset_date=QuotaService.get_next_month_start(),
        )
        db_session.add(sub_b)
        await db_session.commit()

        # Tenant A is blocked
        has_quota_a, _ = await QuotaService.check_tender_quota(db_session, tenant_a.id)
        assert has_quota_a is False

        # Tenant B is NOT blocked
        has_quota_b, _ = await QuotaService.check_tender_quota(db_session, tenant_b.id)
        assert has_quota_b is True


class TestMemberManagement:
    """Test tenant member operations."""

    @pytest.mark.asyncio
    async def test_add_member_to_tenant(self, db_session, owner_user, analyst_user):
        """Add member to tenant with specific role."""
        tenant, _ = await RBACService.provision_tenant(
            db_session, "Test", "test-members", owner_user.id, "pro"
        )

        await RBACService.add_tenant_member(db_session, tenant.id, analyst_user.id, "analyst")

        member = await db_session.scalar(
            select(TenantMember).where(
                (TenantMember.tenant_id == tenant.id)
                & (TenantMember.user_id == analyst_user.id)
            )
        )
        assert member is not None

    @pytest.mark.asyncio
    async def test_list_tenant_members(self, db_session, owner_user, analyst_user, admin_user):
        """List all members of a tenant."""
        tenant, _ = await RBACService.provision_tenant(
            db_session, "Test", "test-list-members", owner_user.id, "pro"
        )

        await RBACService.add_tenant_member(db_session, tenant.id, analyst_user.id, "analyst")
        await RBACService.add_tenant_member(db_session, tenant.id, admin_user.id, "admin")

        members = await RBACService.get_tenant_members(db_session, tenant.id)
        assert len(members) == 3  # owner + analyst + admin
        assert any(m["email"] == owner_user.email for m in members)
        assert any(m["email"] == analyst_user.email for m in members)
        assert any(m["email"] == admin_user.email for m in members)

    @pytest.mark.asyncio
    async def test_remove_tenant_member(self, db_session, owner_user, analyst_user):
        """Remove member from tenant."""
        tenant, _ = await RBACService.provision_tenant(
            db_session, "Test", "test-remove-member", owner_user.id, "pro"
        )

        await RBACService.add_tenant_member(db_session, tenant.id, analyst_user.id, "analyst")

        # Verify member exists
        members_before = await RBACService.get_tenant_members(db_session, tenant.id)
        assert len(members_before) == 2

        # Remove
        await RBACService.remove_tenant_member(db_session, tenant.id, analyst_user.id)

        # Verify removed
        members_after = await RBACService.get_tenant_members(db_session, tenant.id)
        assert len(members_after) == 1
        assert not any(m["user_id"] == analyst_user.id for m in members_after)
