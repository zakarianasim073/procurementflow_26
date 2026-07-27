"""T-036: Quota enforcement — unit + integration tests.

Uses the real QuotaService and real DB (savepoint-isolated).
TenderUsageLog rows are the authoritative usage counter; ClientSubscription
carries the *limit* and requires a SubscriptionPlan FK.
"""
from __future__ import annotations

import uuid
import pytest

from app.models.subscription import ClientSubscription, TenderUsageLog
from app.models.enterprise import Tenant
from app.services.quota_service import QuotaService


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _make_tenant(db, slug_suffix: str = "") -> Tenant:
    t = Tenant(
        id=str(uuid.uuid4()),
        name=f"Tenant {slug_suffix}",
        slug=f"qe-{uuid.uuid4().hex[:8]}{slug_suffix}",
        plan="free",
    )
    db.add(t)
    await db.flush()
    return t


async def _make_subscription(db, tenant_id: str, plan_id: str, limit: int = 100) -> ClientSubscription:
    sub = ClientSubscription(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        plan_id=plan_id,
        status="active",
        tender_quota_limit=limit,
        quota_reset_date=QuotaService.get_next_month_start(),
    )
    db.add(sub)
    await db.flush()
    return sub


async def _log_n_accesses(db, tenant_id: str, n: int):
    """Insert n TenderUsageLog rows this month."""
    for i in range(n):
        db.add(TenderUsageLog(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            tender_id=f"tender-{i}",
            action="view",
            quota_consumed=1,
        ))
    await db.flush()


# ── Tests ─────────────────────────────────────────────────────────────────────

class TestQuotaEnforcementMiddleware:
    """Service-level quota checks (middleware delegates to QuotaService)."""

    @pytest.mark.asyncio
    async def test_fresh_tenant_has_quota(self, db_session, subscription_plan):
        tenant = await _make_tenant(db_session, "-fresh")
        await _make_subscription(db_session, tenant.id, subscription_plan.id, limit=10)
        await db_session.commit()

        has, err = await QuotaService.check_tender_quota(db_session, tenant.id)
        assert has is True
        assert err is None

    @pytest.mark.asyncio
    async def test_quota_exhaustion_returns_blocked(self, db_session, subscription_plan):
        tenant = await _make_tenant(db_session, "-exhausted")
        await _make_subscription(db_session, tenant.id, subscription_plan.id, limit=5)
        # Exhaust by creating 5 usage logs
        await _log_n_accesses(db_session, tenant.id, 5)
        await db_session.commit()

        has, err = await QuotaService.check_tender_quota(db_session, tenant.id)
        assert has is False
        assert err is not None
        assert "exhausted" in err.lower() or "quota" in err.lower()

    @pytest.mark.asyncio
    async def test_post_tenders_with_limited_quota(self, db_session, subscription_plan):
        """Creating subscription with limit=5 and using 5 logs blocks next request."""
        tenant = await _make_tenant(db_session, "-limited")
        await _make_subscription(db_session, tenant.id, subscription_plan.id, limit=5)
        await _log_n_accesses(db_session, tenant.id, 5)
        await db_session.commit()

        quota = await QuotaService.get_tender_quota(db_session, tenant.id)
        assert quota["remaining"] == 0
        assert quota["used"] == 5


class TestQuotaWithLogging:
    """log_tender_access() increments TenderUsageLog rows."""

    @pytest.mark.asyncio
    async def test_log_tender_access_tracks_usage(self, db_session, subscription_plan):
        tenant = await _make_tenant(db_session, "-log")
        await _make_subscription(db_session, tenant.id, subscription_plan.id, limit=100)
        await db_session.commit()

        success = await QuotaService.log_tender_access(db_session, tenant.id, "tender-1", "view")
        assert success is True

        quota = await QuotaService.get_tender_quota(db_session, tenant.id)
        assert quota["used"] == 1
        assert quota["remaining"] == 99

        for i in range(2, 6):
            await QuotaService.log_tender_access(db_session, tenant.id, f"tender-{i}", "view")

        quota = await QuotaService.get_tender_quota(db_session, tenant.id)
        assert quota["used"] == 5

    @pytest.mark.asyncio
    async def test_log_tender_access_blocked_when_exhausted(self, db_session, subscription_plan):
        tenant = await _make_tenant(db_session, "-blocked")
        await _make_subscription(db_session, tenant.id, subscription_plan.id, limit=3)
        await _log_n_accesses(db_session, tenant.id, 3)
        await db_session.commit()

        # Next access should be blocked
        result = await QuotaService.log_tender_access(db_session, tenant.id, "tender-extra", "view")
        assert result is False


class TestQuotaWarnings:
    """Warning threshold activates at 80% usage."""

    @pytest.mark.asyncio
    async def test_warning_below_threshold(self, db_session, subscription_plan):
        tenant = await _make_tenant(db_session, "-below80")
        await _make_subscription(db_session, tenant.id, subscription_plan.id, limit=100)
        await _log_n_accesses(db_session, tenant.id, 79)
        await db_session.commit()

        summary = await QuotaService.get_quota_summary(db_session, tenant.id)
        assert summary["warning_active"] is False

    @pytest.mark.asyncio
    async def test_warning_at_80_percent(self, db_session, subscription_plan):
        tenant = await _make_tenant(db_session, "-at80")
        await _make_subscription(db_session, tenant.id, subscription_plan.id, limit=100)
        await _log_n_accesses(db_session, tenant.id, 80)
        await db_session.commit()

        summary = await QuotaService.get_quota_summary(db_session, tenant.id)
        assert summary["warning_active"] is True
        assert summary["tender_quota"]["percent_used"] == 80.0


class TestQuotaCrossTenantIsolation:
    """Quota state is strictly per-tenant."""

    @pytest.mark.asyncio
    async def test_exhausted_tenant_does_not_block_other(self, db_session, subscription_plan):
        # Tenant A: exhausted
        ta = await _make_tenant(db_session, "-a")
        await _make_subscription(db_session, ta.id, subscription_plan.id, limit=10)
        await _log_n_accesses(db_session, ta.id, 10)

        # Tenant B: fresh
        tb = await _make_tenant(db_session, "-b")
        await _make_subscription(db_session, tb.id, subscription_plan.id, limit=500)
        await db_session.commit()

        has_a, _ = await QuotaService.check_tender_quota(db_session, ta.id)
        has_b, _ = await QuotaService.check_tender_quota(db_session, tb.id)
        assert has_a is False
        assert has_b is True
