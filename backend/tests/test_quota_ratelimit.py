"""T-036: Quota isolation + rate limit tests.

Each test uses the real QuotaService and real TenderUsageLog rows
(not ClientSubscription.tender_quota_used, which is a denormalized
cache column — QuotaService counts TenderUsageLog rows for 'used').
"""
from __future__ import annotations

import uuid
import pytest
from datetime import datetime, timezone, timedelta

from sqlalchemy import select, func

from app.models.enterprise import Tenant
from app.models.subscription import ClientSubscription, TenderUsageLog
from app.services.quota_service import QuotaService
from app.core.tenant_rate_limiter import TenantRateLimiter


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture()
async def tenant_with_subscription(db_session, subscription_plan):
    """Tenant + ClientSubscription with limit=50 and a real plan FK."""
    tenant = Tenant(
        id=str(uuid.uuid4()),
        name="Quota Test Tenant",
        slug=f"qrl-{uuid.uuid4().hex[:8]}",
        plan="pro",
    )
    db_session.add(tenant)
    await db_session.flush()

    sub = ClientSubscription(
        id=str(uuid.uuid4()),
        tenant_id=tenant.id,
        plan_id=subscription_plan.id,
        status="active",
        tender_quota_limit=50,
        quota_reset_date=QuotaService.get_next_month_start(),
    )
    db_session.add(sub)
    await db_session.commit()
    return tenant, sub


# ── Quota tracking ────────────────────────────────────────────────────────────

class TestQuotaTracking:

    @pytest.mark.asyncio
    async def test_get_quota_status_no_subscription(self, db_session):
        """Default quota (no subscription row) returns 100 with 0 used."""
        tenant_id = str(uuid.uuid4())
        quota = await QuotaService.get_tender_quota(db_session, tenant_id)
        assert quota["limit"] == 100
        assert quota["used"] == 0
        assert quota["remaining"] == 100
        assert quota["percent_used"] == 0.0

    @pytest.mark.asyncio
    async def test_get_quota_status_with_subscription(self, db_session, tenant_with_subscription):
        """Subscription limit is respected; 0 logs → 0 used."""
        tenant, sub = tenant_with_subscription
        quota = await QuotaService.get_tender_quota(db_session, tenant.id)
        assert quota["limit"] == 50
        assert quota["used"] == 0
        assert quota["remaining"] == 50
        assert quota["percent_used"] == 0.0

    @pytest.mark.asyncio
    async def test_log_tender_access_consumes_quota(self, db_session, tenant_with_subscription):
        """log_tender_access() creates a TenderUsageLog and increments used."""
        tenant, _ = tenant_with_subscription
        success = await QuotaService.log_tender_access(db_session, tenant.id, "tender-123", "view")
        assert success is True

        quota = await QuotaService.get_tender_quota(db_session, tenant.id)
        assert quota["used"] == 1
        assert quota["remaining"] == 49
        assert quota["percent_used"] == 2.0  # 1/50

    @pytest.mark.asyncio
    async def test_quota_exhaustion_blocks_access(self, db_session, tenant_with_subscription):
        """50 log rows → quota exhausted; next check_tender_quota returns False."""
        tenant, _ = tenant_with_subscription
        for i in range(50):
            db_session.add(TenderUsageLog(
                id=str(uuid.uuid4()),
                tenant_id=tenant.id,
                tender_id=f"t-{i}",
                action="view",
                quota_consumed=1,
            ))
        await db_session.commit()

        ok, err = await QuotaService.check_tender_quota(db_session, tenant.id)
        assert ok is False
        assert err is not None

        logged = await QuotaService.log_tender_access(db_session, tenant.id, "tender-extra")
        assert logged is False

    @pytest.mark.asyncio
    async def test_quota_status_summary(self, db_session, tenant_with_subscription):
        """Summary shows correct plan, used, remaining, status."""
        tenant, sub = tenant_with_subscription
        for i in range(10):
            await QuotaService.log_tender_access(db_session, tenant.id, f"t-{i}")

        summary = await QuotaService.get_quota_summary(db_session, tenant.id)
        assert summary["tender_quota"]["used"] == 10
        assert summary["tender_quota"]["remaining"] == 40
        assert summary["status"] == "ok"
        assert summary["warning_active"] is False  # 20% < 80%

    @pytest.mark.asyncio
    async def test_quota_warning_at_threshold(self, db_session, tenant_with_subscription):
        """Warning fires when ≥ 80% of limit is consumed."""
        tenant, sub = tenant_with_subscription
        # 41 logs out of 50 = 82%
        for i in range(41):
            db_session.add(TenderUsageLog(
                id=str(uuid.uuid4()),
                tenant_id=tenant.id,
                tender_id=f"t-{i}",
                action="view",
                quota_consumed=1,
            ))
        await db_session.commit()

        summary = await QuotaService.get_quota_summary(db_session, tenant.id)
        assert summary["warning_active"] is True
        assert summary["tender_quota"]["percent_used"] == 82.0


# ── Rate limiting ─────────────────────────────────────────────────────────────

class TestRateLimitingPerTenant:

    @pytest.mark.asyncio
    async def test_rate_limiter_free_plan_limits(self):
        limiter = TenantRateLimiter()  # No Redis
        free = await limiter.get_limits("t-free", "free")
        pro = await limiter.get_limits("t-pro", "pro")
        assert free["per_minute"] == 100
        assert free["per_hour"] == 1000
        assert pro["per_minute"] == 500
        assert pro["per_hour"] == 5000

    @pytest.mark.asyncio
    async def test_rate_limiter_enterprise_limits(self):
        limiter = TenantRateLimiter()
        ent = await limiter.get_limits("t-ent", "enterprise")
        assert ent["per_minute"] > pro_val if (pro_val := 500) else True
        # Just check it's larger than pro
        pro = await limiter.get_limits("t-ent", "pro")
        assert ent["per_minute"] > pro["per_minute"]

    @pytest.mark.asyncio
    async def test_rate_limiter_no_redis_allows_all(self):
        """Fail-open: no Redis → all requests pass."""
        limiter = TenantRateLimiter(redis_client=None)
        allowed, err = await limiter.is_allowed("t-1", "/api/tenders", "free")
        assert allowed is True
        assert err is None


# ── Isolation ─────────────────────────────────────────────────────────────────

class TestQuotaIsolation:

    @pytest.mark.asyncio
    async def test_tenant_a_exhaustion_does_not_affect_tenant_b(
        self, db_session, subscription_plan
    ):
        ta = Tenant(id=str(uuid.uuid4()), name="TA", slug=f"ta-{uuid.uuid4().hex[:6]}", plan="free")
        tb = Tenant(id=str(uuid.uuid4()), name="TB", slug=f"tb-{uuid.uuid4().hex[:6]}", plan="pro")
        db_session.add_all([ta, tb])
        await db_session.flush()

        # Subscription rows
        db_session.add(ClientSubscription(
            id=str(uuid.uuid4()), tenant_id=ta.id, plan_id=subscription_plan.id,
            status="active", tender_quota_limit=10,
            quota_reset_date=QuotaService.get_next_month_start(),
        ))
        db_session.add(ClientSubscription(
            id=str(uuid.uuid4()), tenant_id=tb.id, plan_id=subscription_plan.id,
            status="active", tender_quota_limit=100,
            quota_reset_date=QuotaService.get_next_month_start(),
        ))

        # Exhaust TA with 10 logs
        for i in range(10):
            db_session.add(TenderUsageLog(
                id=str(uuid.uuid4()), tenant_id=ta.id, tender_id=f"t{i}", action="view", quota_consumed=1,
            ))
        await db_session.commit()

        ok_a, _ = await QuotaService.check_tender_quota(db_session, ta.id)
        ok_b, _ = await QuotaService.check_tender_quota(db_session, tb.id)
        assert ok_a is False
        assert ok_b is True

    @pytest.mark.asyncio
    async def test_separate_usage_logs_per_tenant(self, db_session):
        # Must create Tenant rows first (TenderUsageLog has FK to tenants)
        ta = Tenant(id=str(uuid.uuid4()), name="TA-sep", slug=f"sep-a-{uuid.uuid4().hex[:6]}", plan="free")
        tb = Tenant(id=str(uuid.uuid4()), name="TB-sep", slug=f"sep-b-{uuid.uuid4().hex[:6]}", plan="free")
        db_session.add_all([ta, tb])
        await db_session.flush()
        tid_a, tid_b = ta.id, tb.id
        db_session.add(TenderUsageLog(
            id=str(uuid.uuid4()), tenant_id=tid_a, tender_id="ta-1", action="view", quota_consumed=1,
        ))
        db_session.add(TenderUsageLog(
            id=str(uuid.uuid4()), tenant_id=tid_b, tender_id="tb-1", action="view", quota_consumed=1,
        ))
        await db_session.commit()

        count_a = await db_session.scalar(
            select(func.count(TenderUsageLog.id)).where(TenderUsageLog.tenant_id == tid_a)
        )
        count_b = await db_session.scalar(
            select(func.count(TenderUsageLog.id)).where(TenderUsageLog.tenant_id == tid_b)
        )
        assert count_a == 1
        assert count_b == 1


# ── Monthly reset ─────────────────────────────────────────────────────────────

class TestMonthlyQuotaReset:

    @pytest.mark.asyncio
    async def test_reset_monthly_quotas(self, db_session, subscription_plan):
        """Subscriptions whose reset_date is in the past get their used counter cleared."""
        past = datetime.now(timezone.utc) - timedelta(days=1)
        tenant = Tenant(
            id=str(uuid.uuid4()), name="ResetTenant",
            slug=f"reset-{uuid.uuid4().hex[:6]}", plan="free",
        )
        db_session.add(tenant)
        await db_session.flush()
        sub = ClientSubscription(
            id=str(uuid.uuid4()),
            tenant_id=tenant.id,
            plan_id=subscription_plan.id,
            status="active",
            tender_quota_limit=100,
            tender_quota_used=50,
            quota_reset_date=past,
        )
        db_session.add(sub)
        await db_session.commit()

        count = await QuotaService.reset_monthly_quotas(db_session)
        assert count >= 1

        refreshed = await db_session.get(ClientSubscription, sub.id)
        assert refreshed.tender_quota_used == 0
        assert refreshed.quota_reset_date > datetime.now(timezone.utc)
