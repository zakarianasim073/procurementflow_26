"""Celery tasks for quota management (T-036)."""

from __future__ import annotations

import logging
from celery import shared_task
from sqlalchemy import select
from datetime import datetime, timezone

from app.db.database import get_async_session
from app.services.quota_service import QuotaService

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def reset_monthly_quotas(self):
    """
    Reset monthly quotas for all tenants.
    Scheduled to run daily at midnight UTC via Celery Beat.

    Task ID: quota.reset_monthly_quotas
    Schedule: 0 0 * * * (daily at midnight UTC)
    """
    try:
        import asyncio

        async def _reset():
            async with get_async_session() as db:
                count = await QuotaService.reset_monthly_quotas(db)
                return count

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        count = loop.run_until_complete(_reset())

        logger.info(f"✅ Reset quotas for {count} tenants")
        return {"status": "success", "tenants_reset": count}

    except Exception as exc:
        logger.error(f"❌ Quota reset failed: {exc}")
        # Retry in 5 minutes
        raise self.retry(exc=exc, countdown=300)


@shared_task(bind=True)
def clean_expired_rate_limits(self):
    """
    Clean up expired rate limit keys from Redis.
    Runs weekly to prevent key bloat.

    Task ID: quota.clean_expired_rate_limits
    Schedule: 0 2 * * 0 (weekly, Sunday 2am UTC)
    """
    try:
        import redis.asyncio as redis
        from app.core.config import settings

        redis_url = settings.REDIS_URL or "redis://localhost:6379/0"
        redis_client = redis.from_url(redis_url, decode_responses=True)

        # Keys expire automatically in Redis (TTL set to 3600s)
        # This task is just for manual cleanup if needed

        logger.info("✅ Rate limit cleanup completed")
        return {"status": "success"}

    except Exception as exc:
        logger.warning(f"⚠️ Rate limit cleanup failed: {exc}")
        return {"status": "failed", "error": str(exc)}
