"""T-029 (DBT-01): Scheduled package-number repair tasks.

Nightly Celery Beat entry repairs broken award→tender FK links via
normalized_package_no, then triggers a lifecycle rebuild so downstream
DNA / competition-intel is based on clean data.
"""
from __future__ import annotations

import logging

from app.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(
    bind=True,
    max_retries=1,
    name="repair_package_nos",
    queue="default",
)
def repair_package_nos(self) -> dict:
    """Back-fill missing procurement_tender_id on award_records_v2.

    1. Run PackageNoRepairService.repair() — bulk UPDATE via normalized_package_no
    2. If rows were repaired, trigger a lifecycle rebuild so procurement_lifecycle
       reflects the updated FK links
    """
    try:
        from app.services.package_no_repair_service import PackageNoRepairService
        result = PackageNoRepairService.repair()

        repaired = result.get("repaired_this_run", 0)
        logger.info(
            "repair_package_nos: repaired=%d remaining=%d rate=%.1f%%",
            repaired,
            result.get("unresolved", 0),
            result.get("resolution_rate_pct", 0),
        )

        if repaired > 0:
            # Rebuild lifecycle so procurement_lifecycle reflects the fixed FKs
            try:
                from app.services.lifecycle_rebuilder_service import LifecycleRebuilderService
                lc = LifecycleRebuilderService.rebuild()
                result["lifecycle_rebuild"] = {
                    "after": lc.get("after"),
                    "matched": lc.get("quality", {}).get("matched"),
                }
            except Exception as exc:
                logger.error("lifecycle rebuild after repair failed: %s", exc)
                result["lifecycle_rebuild_error"] = str(exc)

        return result

    except Exception as exc:
        logger.error("repair_package_nos failed: %s", exc)
        raise self.retry(exc=exc, countdown=300)
