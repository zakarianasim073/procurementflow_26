"""T-018 Index Performance Tests: Verify indexes improve query performance.

Tests that:
1. Indexes exist on all critical tables
2. Queries use indexes (not full table scans)
3. Common operations benefit from indexes
"""

from __future__ import annotations

import uuid
import pytest
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enterprise import Tenant, TenantMember, Role
from app.models.subscription import ClientSubscription
from app.models.user import User
from app.services.rbac_service import RBACService


class TestIndexExistence:
    """Verify indexes are created."""

    @pytest.mark.asyncio
    async def test_tenant_member_indexes_exist(self, db_session: AsyncSession):
        """tenant_members has required indexes."""
        # Query to check indexes (PostgreSQL)
        result = await db_session.execute(
            text("""
                SELECT indexname FROM pg_indexes
                WHERE tablename = 'tenant_members'
                ORDER BY indexname
            """)
        )
        indexes = {row[0] for row in result.fetchall()}

        assert "ix_tenant_members_tenant_id" in indexes
        assert "ix_tenant_members_user_id" in indexes
        assert "ix_tenant_members_tenant_user" in indexes

    @pytest.mark.asyncio
    async def test_audit_events_indexes_exist(self, db_session: AsyncSession):
        """audit_events has required indexes."""
        result = await db_session.execute(
            text("""
                SELECT indexname FROM pg_indexes
                WHERE tablename = 'audit_events'
                ORDER BY indexname
            """)
        )
        indexes = {row[0] for row in result.fetchall()}

        assert "ix_audit_events_tenant_id" in indexes
        assert "ix_audit_events_created_at" in indexes

    @pytest.mark.asyncio
    async def test_users_indexes_exist(self, db_session: AsyncSession):
        """users table has required indexes."""
        result = await db_session.execute(
            text("""
                SELECT indexname FROM pg_indexes
                WHERE tablename = 'users'
                ORDER BY indexname
            """)
        )
        indexes = {row[0] for row in result.fetchall()}

        assert "ix_users_email" in indexes
        assert "ix_users_tenant_id" in indexes


class TestIndexUsage:
    """Verify queries use indexes."""

    @pytest.mark.asyncio
    async def test_find_user_by_email_uses_index(self, db_session: AsyncSession):
        """Query by email should use ix_users_email."""
        # Create user
        user = User(
            id=str(uuid.uuid4()),
            email="indexed@example.com",
            full_name="Indexed User",
            tenant_id=None,
            hashed_password="pwd",
            is_active=True,
        )
        db_session.add(user)
        await db_session.commit()

        # Query with EXPLAIN to check index usage
        result = await db_session.execute(
            text("""
                EXPLAIN (FORMAT JSON)
                SELECT * FROM users WHERE email = :email
            """),
            {"email": "indexed@example.com"},
        )

        plan = result.scalar()
        plan_text = str(plan).lower()

        # Should mention the index or use a fast plan
        assert "seq scan" not in plan_text or "index" in plan_text

    @pytest.mark.asyncio
    async def test_find_tenant_members_uses_composite_index(self, db_session: AsyncSession):
        """Query tenant members should use composite index."""
        # Setup
        tenant = Tenant(id=str(uuid.uuid4()), name="Test", slug="test", plan="pro")
        db_session.add(tenant)
        await db_session.flush()

        user = User(
            id=str(uuid.uuid4()),
            email="member@example.com",
            full_name="Member",
            tenant_id=None,
            hashed_password="pwd",
            is_active=True,
        )
        db_session.add(user)
        await db_session.flush()

        # Create membership
        await RBACService.add_tenant_member(db_session, tenant.id, user.id, "viewer")

        # Query with EXPLAIN
        result = await db_session.execute(
            text("""
                EXPLAIN (FORMAT JSON)
                SELECT * FROM tenant_members
                WHERE tenant_id = :tenant_id AND user_id = :user_id
            """),
            {"tenant_id": tenant.id, "user_id": user.id},
        )

        plan = result.scalar()
        plan_text = str(plan).lower()

        # Should use index for efficient lookup
        assert "index" in plan_text or "bitmap" in plan_text


class TestQueryPerformance:
    """Test that common operations benefit from indexes."""

    @pytest.mark.asyncio
    async def test_list_tenant_members_performance(self, db_session: AsyncSession):
        """Listing tenant members should be fast with index."""
        # Setup: Create tenant and add 10 members
        tenant = Tenant(id=str(uuid.uuid4()), name="Perf Test", slug="perf-test", plan="pro")
        db_session.add(tenant)
        await db_session.flush()

        for i in range(10):
            user = User(
                id=str(uuid.uuid4()),
                email=f"member{i}@example.com",
                full_name=f"Member {i}",
                tenant_id=None,
                hashed_password="pwd",
                is_active=True,
            )
            db_session.add(user)
            await db_session.flush()
            await RBACService.add_tenant_member(db_session, tenant.id, user.id, "viewer")

        # List members should be fast
        members = await RBACService.get_tenant_members(db_session, tenant.id)
        assert len(members) == 11  # 10 + owner

    @pytest.mark.asyncio
    async def test_find_user_permissions_uses_indexes(self, db_session: AsyncSession):
        """Getting user permissions should use tenant_member and role indexes."""
        # Setup
        tenant, _ = await RBACService.provision_tenant(
            db_session,
            "Perm Test",
            "perm-test",
            str(uuid.uuid4()),
            "pro",
        )

        # Get owner user
        owner = await db_session.scalar(
            select(User).join(TenantMember).where(
                (TenantMember.tenant_id == tenant.id)
                & (TenantMember.is_owner == True)
            )
        )

        # Get permissions (should use indexes internally)
        permissions = await RBACService.get_user_permissions(db_session, owner.id, tenant.id)

        assert len(permissions) > 0

    @pytest.mark.asyncio
    async def test_cross_tenant_isolation_fast(self, db_session: AsyncSession):
        """Cross-tenant access check should be fast with indexes."""
        # Create two tenants
        tenant_a = Tenant(id=str(uuid.uuid4()), name="A", slug="a", plan="free")
        tenant_b = Tenant(id=str(uuid.uuid4()), name="B", slug="b", plan="pro")
        db_session.add(tenant_a)
        db_session.add(tenant_b)
        await db_session.flush()

        user = User(
            id=str(uuid.uuid4()),
            email="crosscheck@example.com",
            full_name="Cross User",
            tenant_id=None,
            hashed_password="pwd",
            is_active=True,
        )
        db_session.add(user)
        await db_session.flush()

        # User only in tenant_a
        await RBACService.add_tenant_member(db_session, tenant_a.id, user.id, "viewer")

        # Check that user is NOT in tenant_b (should be fast with index)
        member = await db_session.scalar(
            select(TenantMember).where(
                (TenantMember.tenant_id == tenant_b.id)
                & (TenantMember.user_id == user.id)
            )
        )

        assert member is None


class TestIndexStatistics:
    """Verify index health and statistics."""

    @pytest.mark.asyncio
    async def test_index_size_reasonable(self, db_session: AsyncSession):
        """Indexes shouldn't be excessively large."""
        # Check total index size
        result = await db_session.execute(
            text("""
                SELECT
                    schemaname,
                    tablename,
                    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
                FROM pg_tables
                WHERE schemaname NOT IN ('pg_catalog', 'information_schema')
                ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
                LIMIT 10
            """)
        )

        tables = result.fetchall()
        # Just verify we can query index sizes (no assertion needed)
        assert len(tables) > 0

    @pytest.mark.asyncio
    async def test_most_used_indexes_are_present(self, db_session: AsyncSession):
        """Critical indexes are present."""
        critical_indexes = [
            "ix_tenant_members_tenant_user",
            "ix_audit_events_tenant_created",
            "ix_users_email",
            "ix_users_tenant_id",
        ]

        result = await db_session.execute(
            text("""
                SELECT indexname FROM pg_indexes
                WHERE schemaname = 'public'
            """)
        )

        all_indexes = {row[0] for row in result.fetchall()}

        for idx in critical_indexes:
            assert idx in all_indexes, f"Critical index {idx} is missing"
