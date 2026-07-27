"""Per-tenant quota management: track and enforce monthly limits (T-036)."""

from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.subscription import TenderUsageLog, ClientSubscription

logger = logging.getLogger(__name__)


class QuotaService:
    """Manage per-tenant tender and API quotas."""

    # Quota types
    QUOTA_TENDER_LIMIT = "tender_limit"
    QUOTA_API_REQUESTS = "api_requests"

    @staticmethod
    def get_current_month_start() -> datetime:
        """Get start of current month (UTC)."""
        now = datetime.now(timezone.utc)
        return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    @staticmethod
    def get_next_month_start() -> datetime:
        """Get start of next month (UTC)."""
        current_start = QuotaService.get_current_month_start()
        # Add 32 days and reset to 1st (handles all month lengths)
        next_month = (current_start + timedelta(days=32)).replace(day=1)
        return next_month

    @staticmethod
    async def get_tender_quota(
        db: AsyncSession,
        tenant_id: str,
    ) -> Dict[str, int | str]:
        """Get current tender quota status for tenant.

        Returns:
            {
                "limit": int,           # monthly limit
                "used": int,            # used this month
                "remaining": int,       # remaining
                "reset_date": str,      # ISO date of next reset
                "percent_used": float,  # 0-100
            }
        """
        sub = await db.scalar(
            select(ClientSubscription).where(ClientSubscription.tenant_id == tenant_id)
        )

        if not sub:
            # No subscription: unlimited (or free tier default)
            return {
                "limit": 100,
                "used": 0,
                "remaining": 100,
                "reset_date": QuotaService.get_next_month_start().isoformat(),
                "percent_used": 0.0,
            }

        # Count tenders accessed this month
        month_start = QuotaService.get_current_month_start()
        used = await db.scalar(
            select(func.count(TenderUsageLog.id)).where(
                and_(
                    TenderUsageLog.tenant_id == tenant_id,
                    TenderUsageLog.created_at >= month_start,
                )
            )
        )
        used = used or 0

        limit = sub.tender_quota_limit or 100
        remaining = max(0, limit - used)
        reset_date = QuotaService.get_next_month_start()
        percent = (used / limit * 100) if limit > 0 else 0

        return {
            "limit": limit,
            "used": used,
            "remaining": remaining,
            "reset_date": reset_date.isoformat(),
            "percent_used": min(100.0, percent),
        }

    @staticmethod
    async def check_tender_quota(
        db: AsyncSession,
        tenant_id: str,
    ) -> tuple[bool, Optional[str]]:
        """Check if tenant has remaining tender quota.

        Returns:
            (has_quota, error_message)
        """
        quota = await QuotaService.get_tender_quota(db, tenant_id)

        if quota["remaining"] <= 0:
            return False, f"Tender quota exhausted ({quota['used']}/{quota['limit']}). Reset {quota['reset_date']}"

        return True, None

    @staticmethod
    async def log_tender_access(
        db: AsyncSession,
        tenant_id: str,
        tender_id: str,
        action: str = "view",  # view, compare, analyze, etc.
    ) -> bool:
        """Log a tender access for quota tracking.

        Returns: True if logged successfully, False if quota exceeded.
        """
        # Check quota first
        has_quota, error = await QuotaService.check_tender_quota(db, tenant_id)
        if not has_quota:
            logger.warning(f"Quota exhausted: tenant={tenant_id}")
            return False

        # Log the access
        log_entry = TenderUsageLog(
            tenant_id=tenant_id,
            tender_id=tender_id,
            action=action,
            quota_consumed=1,
        )
        db.add(log_entry)
        await db.flush()
        return True

    @staticmethod
    async def get_quota_summary(
        db: AsyncSession,
        tenant_id: str,
    ) -> Dict:
        """Get comprehensive quota summary for tenant."""
        tender_quota = await QuotaService.get_tender_quota(db, tenant_id)

        # Eager-load the plan relationship: async SQLAlchemy can't implicitly
        # lazy-load it (raises MissingGreenlet). SubscriptionPlan exposes `name`
        # (e.g. "Enterprise"), not `.value`.
        from sqlalchemy.orm import selectinload
        sub = await db.scalar(
            select(ClientSubscription)
            .options(selectinload(ClientSubscription.plan))
            .where(ClientSubscription.tenant_id == tenant_id)
        )

        return {
            "tenant_id": tenant_id,
            "plan": (sub.plan.name if sub and sub.plan else "free"),
            "tender_quota": tender_quota,
            "quota_reset_date": tender_quota["reset_date"],
            "status": "ok" if tender_quota["remaining"] > 0 else "exhausted",
            "warning_threshold": 0.8,  # Warn at 80% usage
            "warning_active": tender_quota["percent_used"] >= 80,
        }

    @staticmethod
    async def reset_monthly_quotas(
        db: AsyncSession,
    ) -> int:
        """Reset all tenant quotas for new month (called by scheduler).

        Returns: number of quotas reset.
        """
        subs = await db.execute(select(ClientSubscription))
        count = 0

        for sub in subs.scalars():
            if sub.quota_reset_date and sub.quota_reset_date <= datetime.now(timezone.utc):
                sub.tender_quota_used = 0
                sub.quota_reset_date = QuotaService.get_next_month_start()
                count += 1

        await db.commit()
        logger.info(f"Reset quotas for {count} tenants")
        return count
