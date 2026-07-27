"""
Shared helpers for v1 API routers.
Contains functions that were previously defined inline in main.py.
"""

import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.core.config import settings as boq_settings
from app.db.base import get_session_factory


def clamp_limit(value: int = 50, *, default: int = 50, minimum: int = 1, maximum: int = 200) -> int:
    """Clamp ad-hoc list endpoint limits to a bounded page size."""
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = default
    return max(minimum, min(parsed, maximum))


def normalize_offset(value: int = 0) -> int:
    """Normalize ad-hoc list endpoint offsets."""
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = 0
    return max(0, parsed)


def redis_broker_available() -> bool:
    broker_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    try:
        import redis as _redis

        client = _redis.from_url(broker_url, socket_connect_timeout=1, socket_timeout=1)
        return client.ping()
    except Exception:
        return False


async def load_tender_snapshot(tender_id: str) -> Optional[Dict[str, Any]]:
    """Load a tender summary from PostgreSQL for endpoints that used JSON snapshots."""
    from sqlalchemy import select
    from app.models.intelligence import ProcurementLifecycle, ProcurementTender, APPRecord
    from app.services.intelligence_base import IntelligenceBaseService

    package_no = IntelligenceBaseService.normalize_package_no(tender_id)
    sf = get_session_factory()
    async with sf() as session:
        lifecycle_result = await session.execute(
            select(ProcurementLifecycle)
            .where(ProcurementLifecycle.package_no == package_no)
            .order_by(ProcurementLifecycle.award_date.desc().nullslast())
        )
        lifecycle = lifecycle_result.scalars().first()
        if lifecycle:
            return {
                "tender_id": lifecycle.package_no,
                "title": lifecycle.title or "",
                "procuring_entity": lifecycle.pe_office or "",
                "deadline": lifecycle.award_date or "",
                "estimated_value_bdt": lifecycle.estimated_cost_bdt or 0,
                "detected_nature": lifecycle.procurement_method or "",
                "status": lifecycle.match_type or "",
            }

        app_result = await session.execute(
            select(ProcurementTender, APPRecord)
            .join(APPRecord, APPRecord.procurement_tender_id == ProcurementTender.id)
            .where(ProcurementTender.package_no == package_no)
        )
        row = app_result.first()
        if row:
            tender, app_record = row
            return {
                "tender_id": tender.package_no,
                "title": app_record.title or tender.title or "",
                "procuring_entity": tender.pe_office or "",
                "deadline": app_record.deadline or "",
                "estimated_value_bdt": app_record.estimated_cost_bdt or 0,
                "detected_nature": tender.procurement_method or "",
                "status": app_record.status or tender.match_type or "",
            }
    return None


async def load_tender_overview(limit: int = 5000) -> List[Dict[str, Any]]:
    from app.services.intelligence_data_service_facade import IntelligenceDataServiceFacade as IntelligenceDataService

    sf = get_session_factory()
    async with sf() as session:
        svc = IntelligenceDataService(session)
        result = await svc.query_lifecycle(limit=limit)
        return result["records"]


async def run_legacy_json_sync() -> None:
    """Run legacy JSON sync on startup if needed."""
    import asyncio
    import logging
    from app.db.base import get_session_factory
    from app.services.intelligence_data_service import ImportProgress
    from app.services.intelligence_data_service_facade import IntelligenceDataServiceFacade as IntelligenceDataService

    logger = logging.getLogger("procureflow")
    progress = ImportProgress()

    try:
        sf = get_session_factory()
        async with sf() as session:
            svc = IntelligenceDataService(session)
            # EXISTS stops at the first row; counting all 8 tables here cost a
            # full scan of ~5.5M rows just to answer "is anything loaded".
            populated = await svc.dashboard.has_any_rows("app_records", "awards")
            if populated["app_records"] and populated["awards"]:
                existing = await svc.get_import_counts()
                progress.state = "completed"
                progress.started = True
                progress.current_phase = "skipped_existing_data"
                progress.summary = {"skipped": 1, **existing}
                regime_summary = await svc.backfill_tender_regimes()
                progress.summary["regime_backfill"] = regime_summary
                logger.info("Legacy JSON sync skipped: PostgreSQL already populated (%s)", existing)
                return

            summary = await svc.import_existing_json_data(progress=progress)
            regime_summary = await svc.backfill_tender_regimes()
            summary["regime_backfill"] = regime_summary
        logger.info("Legacy JSON sync complete: %s", summary)
    except asyncio.CancelledError:
        progress.state = "cancelled"
        progress.error = "cancelled"
        raise
    except Exception as e:
        progress.state = "failed"
        progress.error = str(e)
        logger.exception("Legacy JSON sync failed")
