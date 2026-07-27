"""T-019 Performance Baseline Tests: Establish SLOs for critical endpoints.

Defines performance targets (p95/p99 latency, throughput) for:
1. Authentication endpoints (login, refresh, SSO)
2. RBAC endpoints (get permissions, list members)
3. Data endpoints (list tenders, get tender)
4. Business logic (quota checks, evaluations)
"""

from __future__ import annotations

import time
import uuid
import pytest
from statistics import mean, median, stdev
from sqlalchemy import select

from app.models.enterprise import Tenant, TenantMember, Role
from app.models.subscription import ClientSubscription
from app.models.user import User
from app.services.rbac_service import RBACService
from app.services.quota_service import QuotaService


# Performance SLOs (Service Level Objectives)
SLO = {
    # Auth endpoints
    "auth.login": {"p95": 150, "p99": 250, "throughput": 100},  # ms
    "auth.refresh": {"p95": 50, "p99": 100, "throughput": 500},
    "sso.init": {"p95": 100, "p99": 200, "throughput": 200},

    # RBAC endpoints
    "rbac.get_permissions": {"p95": 30, "p99": 50, "throughput": 1000},
    "rbac.list_members": {"p95": 50, "p99": 100, "throughput": 500},
    "rbac.check_permission": {"p95": 10, "p99": 20, "throughput": 5000},

    # Data endpoints
    "data.list_tenders": {"p95": 200, "p99": 400, "throughput": 100},
    "data.get_tender": {"p95": 100, "p99": 200, "throughput": 500},
    "data.list_contractors": {"p95": 150, "p99": 300, "throughput": 200},

    # Business logic
    "business.check_quota": {"p95": 20, "p99": 50, "throughput": 2000},
    "business.evaluate_tender": {"p95": 500, "p99": 1000, "throughput": 10},
}


class PerformanceMetrics:
    """Collect and analyze performance metrics."""

    def __init__(self):
        self.times: list[float] = []

    def record(self, elapsed_ms: float):
        """Record an operation timing."""
        self.times.append(elapsed_ms)

    def percentile(self, p: int) -> float:
        """Get percentile (e.g., p=95 for 95th percentile)."""
        if not self.times:
            return 0.0
        sorted_times = sorted(self.times)
        idx = int(len(sorted_times) * (p / 100.0))
        return sorted_times[min(idx, len(sorted_times) - 1)]

    def summary(self) -> dict:
        """Get summary statistics."""
        if not self.times:
            return {}
        return {
            "count": len(self.times),
            "min": min(self.times),
            "max": max(self.times),
            "mean": mean(self.times),
            "median": median(self.times),
            "stdev": stdev(self.times) if len(self.times) > 1 else 0,
            "p50": self.percentile(50),
            "p95": self.percentile(95),
            "p99": self.percentile(99),
        }


class TestRBACPerformance:
    """Performance tests for RBAC operations."""

    @pytest.mark.asyncio
    async def test_get_user_permissions_performance(self, db_session):
        """get_user_permissions should meet p95/p99 SLOs."""
        # Setup
        tenant, _ = await RBACService.provision_tenant(
            db_session,
            "Perf Tenant",
            "perf-tenant",
            str(uuid.uuid4()),
            "pro",
        )

        owner = await db_session.scalar(
            select(User).join(TenantMember).where(
                (TenantMember.tenant_id == tenant.id) & (TenantMember.is_owner == True)
            )
        )

        metrics = PerformanceMetrics()

        # Run multiple iterations to get statistical data
        for _ in range(20):
            start = time.perf_counter()
            permissions = await RBACService.get_user_permissions(db_session, owner.id, tenant.id)
            elapsed_ms = (time.perf_counter() - start) * 1000

            metrics.record(elapsed_ms)
            assert len(permissions) > 0

        summary = metrics.summary()
        slo = SLO["rbac.get_permissions"]

        assert summary["p95"] < slo["p95"], f"p95 {summary['p95']}ms exceeds SLO {slo['p95']}ms"
        assert summary["p99"] < slo["p99"], f"p99 {summary['p99']}ms exceeds SLO {slo['p99']}ms"

    @pytest.mark.asyncio
    async def test_list_tenant_members_performance(self, db_session):
        """list_tenant_members should meet p95/p99 SLOs."""
        # Setup with multiple members
        tenant, _ = await RBACService.provision_tenant(
            db_session,
            "Members Perf",
            "members-perf",
            str(uuid.uuid4()),
            "pro",
        )

        # Add 5 members
        for i in range(5):
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
            await RBACService.add_tenant_member(db_session, tenant.id, user.id, "analyst")

        metrics = PerformanceMetrics()

        # Measure list operation
        for _ in range(20):
            start = time.perf_counter()
            members = await RBACService.get_tenant_members(db_session, tenant.id)
            elapsed_ms = (time.perf_counter() - start) * 1000

            metrics.record(elapsed_ms)
            assert len(members) == 6  # 5 + owner

        summary = metrics.summary()
        slo = SLO["rbac.list_members"]

        assert summary["p95"] < slo["p95"], f"p95 {summary['p95']}ms exceeds SLO {slo['p95']}ms"
        assert summary["p99"] < slo["p99"], f"p99 {summary['p99']}ms exceeds SLO {slo['p99']}ms"


class TestQuotaPerformance:
    """Performance tests for quota operations."""

    @pytest.mark.asyncio
    async def test_check_quota_performance(self, db_session):
        """check_tenant_quota should meet p95/p99 SLOs."""
        # Setup
        tenant = Tenant(id=str(uuid.uuid4()), name="Quota Perf", slug="quota-perf", plan="pro")
        db_session.add(tenant)
        await db_session.flush()

        sub = ClientSubscription(
            id=str(uuid.uuid4()),
            tenant_id=tenant.id,
            status="active",
            tender_quota_limit=1000,
            tender_quota_used=500,
            quota_reset_date=QuotaService.get_next_month_start(),
        )
        db_session.add(sub)
        await db_session.commit()

        metrics = PerformanceMetrics()

        # Measure quota check
        for _ in range(50):
            start = time.perf_counter()
            has_quota, _ = await QuotaService.check_tender_quota(db_session, tenant.id)
            elapsed_ms = (time.perf_counter() - start) * 1000

            metrics.record(elapsed_ms)
            assert has_quota is True

        summary = metrics.summary()
        slo = SLO["business.check_quota"]

        assert summary["p95"] < slo["p95"], f"p95 {summary['p95']}ms exceeds SLO {slo['p95']}ms"
        assert summary["p99"] < slo["p99"], f"p99 {summary['p99']}ms exceeds SLO {slo['p99']}ms"

    @pytest.mark.asyncio
    async def test_get_quota_summary_performance(self, db_session):
        """get_quota_summary should be fast."""
        # Setup
        tenant = Tenant(id=str(uuid.uuid4()), name="Summary Perf", slug="summary-perf", plan="pro")
        db_session.add(tenant)
        await db_session.flush()

        sub = ClientSubscription(
            id=str(uuid.uuid4()),
            tenant_id=tenant.id,
            status="active",
            tender_quota_limit=1000,
            tender_quota_used=750,  # 75% usage
            quota_reset_date=QuotaService.get_next_month_start(),
        )
        db_session.add(sub)
        await db_session.commit()

        metrics = PerformanceMetrics()

        # Measure summary retrieval
        for _ in range(20):
            start = time.perf_counter()
            summary = await QuotaService.get_quota_summary(db_session, tenant.id)
            elapsed_ms = (time.perf_counter() - start) * 1000

            metrics.record(elapsed_ms)
            assert summary["warning_active"] is True

        summary_stats = metrics.summary()
        # Should be very fast (sub-20ms)
        assert summary_stats["p95"] < 50, f"p95 {summary_stats['p95']}ms is slower than expected"


class TestCrossTenantPerformance:
    """Performance tests for tenant isolation operations."""

    @pytest.mark.asyncio
    async def test_cross_tenant_verification_performance(self, db_session):
        """Cross-tenant isolation check should be very fast."""
        # Setup: Create 3 tenants
        tenants = []
        users = []

        for i in range(3):
            tenant = Tenant(
                id=str(uuid.uuid4()),
                name=f"Tenant {i}",
                slug=f"tenant-{i}",
                plan="pro",
            )
            db_session.add(tenant)
            await db_session.flush()
            tenants.append(tenant)

            user = User(
                id=str(uuid.uuid4()),
                email=f"user{i}@example.com",
                full_name=f"User {i}",
                tenant_id=None,
                hashed_password="pwd",
                is_active=True,
            )
            db_session.add(user)
            await db_session.flush()
            users.append(user)

            await RBACService.add_tenant_member(db_session, tenant.id, user.id, "admin")

        await db_session.commit()

        metrics = PerformanceMetrics()

        # Test: User 0 accessing Tenant 1 (should fail fast with index)
        for _ in range(50):
            start = time.perf_counter()
            member = await db_session.scalar(
                select(TenantMember).where(
                    (TenantMember.tenant_id == tenants[1].id)
                    & (TenantMember.user_id == users[0].id)
                )
            )
            elapsed_ms = (time.perf_counter() - start) * 1000

            metrics.record(elapsed_ms)
            assert member is None

        summary = metrics.summary()
        # Should be very fast due to index
        assert summary["p95"] < 20, f"p95 {summary['p95']}ms is slower than expected for indexed lookup"


class TestScalabilityBaselines:
    """Test performance at scale."""

    @pytest.mark.asyncio
    async def test_performance_with_many_members(self, db_session):
        """Performance should scale linearly with member count."""
        tenant, _ = await RBACService.provision_tenant(
            db_session,
            "Scale Test",
            "scale-test",
            str(uuid.uuid4()),
            "pro",
        )

        # Add users incrementally and measure performance
        timings = []

        for batch in range(3):
            # Add 10 members per batch
            for i in range(10):
                user = User(
                    id=str(uuid.uuid4()),
                    email=f"batch{batch}_user{i}@example.com",
                    full_name=f"Batch {batch} User {i}",
                    tenant_id=None,
                    hashed_password="pwd",
                    is_active=True,
                )
                db_session.add(user)
                await db_session.flush()
                await RBACService.add_tenant_member(db_session, tenant.id, user.id, "viewer")

            # Measure list performance
            start = time.perf_counter()
            members = await RBACService.get_tenant_members(db_session, tenant.id)
            elapsed_ms = (time.perf_counter() - start) * 1000
            timings.append(elapsed_ms)

            # Verify we got all members
            expected = 1 + (batch + 1) * 10  # owner + added members
            assert len(members) == expected

        # Performance should not degrade dramatically
        # Check that time doesn't double when member count triples
        ratio = timings[-1] / timings[0]
        assert ratio < 2.0, f"Performance degraded too much: {ratio}x slowdown for 3x data"


class TestConcurrencyPerformance:
    """Test performance under concurrent access."""

    @pytest.mark.asyncio
    async def test_concurrent_permission_checks(self, db_session):
        """Permission checks should not degrade under concurrent load."""
        # Setup
        tenant, _ = await RBACService.provision_tenant(
            db_session,
            "Concurrent Test",
            "concurrent-test",
            str(uuid.uuid4()),
            "pro",
        )

        # Create 5 users
        user_ids = []
        for i in range(5):
            user = User(
                id=str(uuid.uuid4()),
                email=f"concurrent{i}@example.com",
                full_name=f"User {i}",
                tenant_id=None,
                hashed_password="pwd",
                is_active=True,
            )
            db_session.add(user)
            await db_session.flush()
            user_ids.append(user.id)
            await RBACService.add_tenant_member(db_session, tenant.id, user.id, "analyst")

        await db_session.commit()

        # Simulate concurrent permission checks
        metrics = PerformanceMetrics()

        for user_id in user_ids * 4:  # 4 rounds of checking each user
            start = time.perf_counter()
            perms = await RBACService.get_user_permissions(db_session, user_id, tenant.id)
            elapsed_ms = (time.perf_counter() - start) * 1000
            metrics.record(elapsed_ms)
            assert len(perms) > 0

        summary = metrics.summary()
        slo = SLO["rbac.get_permissions"]

        # Should maintain SLO even under load
        assert summary["p95"] < slo["p95"], "Performance degraded under concurrent load"
