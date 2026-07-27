"""Celery tasks for analytics warehouse refresh (T-020)."""

import logging
from celery import shared_task
from app.db.database import get_async_session
from app.services.analytics_warehouse import AnalyticsWarehouseService

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def refresh_warehouse_facts(self):
    """Hourly task: Refresh fact tables (tenders, awards, bids).

    Syncs all changes from last 24 hours to keep facts up-to-date.
    """
    try:
        import asyncio

        async def do_refresh():
            async with get_async_session() as db:
                results = await AnalyticsWarehouseService.refresh_facts(db, hours_back=24)
                logger.info(f"Warehouse fact refresh: {results}")
                return results

        result = asyncio.run(do_refresh())
        return {"status": "success", "results": result}

    except Exception as exc:
        logger.error(f"Warehouse fact refresh failed: {exc}")
        # Retry with exponential backoff: 5min, 10min, 20min
        raise self.retry(exc=exc, countdown=300 * (2 ** self.request.retries))


@shared_task(bind=True, max_retries=2)
def refresh_warehouse_dimensions(self):
    """Daily task: Refresh dimension tables (agencies, contractors, etc).

    Keeps dimension data in sync with source systems.
    """
    try:
        import asyncio

        async def do_refresh():
            async with get_async_session() as db:
                results = await AnalyticsWarehouseService.refresh_dimensions(db)
                logger.info(f"Warehouse dimension refresh: {results}")
                return results

        result = asyncio.run(do_refresh())
        return {"status": "success", "results": result}

    except Exception as exc:
        logger.error(f"Warehouse dimension refresh failed: {exc}")
        # Retry with exponential backoff: 5min, 10min
        raise self.retry(exc=exc, countdown=300 * (2 ** self.request.retries))


@shared_task(bind=True, max_retries=2)
def refresh_materialized_views(self):
    """Daily task: Refresh materialized views for analytics queries.

    Materializes aggregations for dashboard queries.
    """
    try:
        import asyncio

        async def do_refresh():
            async with get_async_session() as db:
                results = await AnalyticsWarehouseService.refresh_materialized_views(db)
                logger.info(f"Materialized view refresh: {results}")
                return results

        result = asyncio.run(do_refresh())
        return {"status": "success", "results": result}

    except Exception as exc:
        logger.error(f"Materialized view refresh failed: {exc}")
        # Retry with exponential backoff: 5min, 10min
        raise self.retry(exc=exc, countdown=300 * (2 ** self.request.retries))


@shared_task
def get_warehouse_health_check():
    """Periodic health check: Verify warehouse is populated and current.

    Used for monitoring/alerting on data staleness.
    """
    try:
        import asyncio
        from datetime import datetime, timedelta, timezone

        async def check_health():
            async with get_async_session() as db:
                stats = await AnalyticsWarehouseService.get_warehouse_stats(db)

                # Check that we have data
                if stats.get("fact_tenders", 0) == 0:
                    logger.warning("Warehouse has no tender data")
                    return {"status": "warning", "message": "No data in warehouse", "stats": stats}

                logger.info(f"Warehouse health OK: {stats}")
                return {"status": "healthy", "stats": stats}

        result = asyncio.run(check_health())
        return result

    except Exception as exc:
        logger.error(f"Warehouse health check failed: {exc}")
        return {"status": "error", "message": str(exc)}
