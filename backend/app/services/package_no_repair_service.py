"""Package-number repair pipeline — T-029 / DBT-01.

Uses normalized_package_no (ADR-016) to back-fill broken procurement_tender_id
foreign keys on award_records_v2.  52K+ awards were ingested before the join key
was normalised; this service resolves the backlog and keeps it clear via the
nightly Celery Beat task.

Design:
  - Single bulk UPDATE — one SQL round-trip for the full repair pass
  - Idempotent — safe to run repeatedly; only touches rows with NULL FK
  - Returns rich stats so the data-quality endpoint can surface them to the UI
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict

from sqlalchemy import text

from app.db.database import get_sync_engine

logger = logging.getLogger(__name__)


class PackageNoRepairService:
    """Repair broken award→tender FK links via normalized_package_no."""

    @staticmethod
    def repair() -> Dict[str, Any]:
        """Run the repair pass.

        Resolves award_records_v2 rows where procurement_tender_id IS NULL by
        joining on normalized_package_no → procurement_tenders.

        Returns a stats dict suitable for JSON serialisation.
        """
        engine = get_sync_engine()
        with engine.begin() as conn:
            before_unresolved = conn.execute(text(
                "SELECT COUNT(*) FROM award_records_v2 WHERE procurement_tender_id IS NULL"
            )).scalar_one()

            if before_unresolved == 0:
                return _stats(0, 0, 0, 0, conn)

            # Bulk FK repair: match via normalized_package_no
            repaired = conn.execute(text("""
                UPDATE award_records_v2 av2
                SET procurement_tender_id = pt.id,
                    updated_at            = NOW()
                FROM (
                    -- Pick the most-recently-updated tender when package_no is
                    -- non-unique (shouldn't happen, but guards the UPDATE)
                    SELECT DISTINCT ON (normalized_package_no)
                        id, normalized_package_no
                    FROM procurement_tenders
                    WHERE normalized_package_no IS NOT NULL
                      AND normalized_package_no <> ''
                    ORDER BY normalized_package_no, updated_at DESC NULLS LAST
                ) pt
                WHERE av2.normalized_package_no = pt.normalized_package_no
                  AND av2.normalized_package_no IS NOT NULL
                  AND av2.normalized_package_no <> ''
                  AND av2.procurement_tender_id IS NULL
            """)).rowcount

            return _stats(before_unresolved, repaired, conn=conn)

    @staticmethod
    def get_quality_metrics() -> Dict[str, Any]:
        """Return current data-quality metrics without running a repair."""
        engine = get_sync_engine()
        with engine.connect() as conn:
            return _stats(conn=conn)


# ── helpers ────────────────────────────────────────────────────────────────────

def _stats(
    before_unresolved: int = None,
    repaired: int = None,
    still_unresolved: int = None,
    unresolvable: int = None,
    conn=None,
) -> Dict[str, Any]:
    """Gather quality counters and format the result dict."""
    if conn is not None:
        total = conn.execute(text(
            "SELECT COUNT(*) FROM award_records_v2"
        )).scalar_one()
        resolved = conn.execute(text(
            "SELECT COUNT(*) FROM award_records_v2 WHERE procurement_tender_id IS NOT NULL"
        )).scalar_one()
        still_unresolved = conn.execute(text(
            "SELECT COUNT(*) FROM award_records_v2 WHERE procurement_tender_id IS NULL"
        )).scalar_one()
        unresolvable = conn.execute(text(
            "SELECT COUNT(*) FROM award_records_v2 "
            "WHERE procurement_tender_id IS NULL "
            "  AND (normalized_package_no IS NULL OR normalized_package_no = '')"
        )).scalar_one()
    else:
        total = resolved = still_unresolved = unresolvable = 0

    resolution_rate = round(resolved / total * 100, 2) if total else 0.0

    result = {
        "total_award_records": total,
        "resolved": resolved,
        "unresolved": still_unresolved,
        "unresolvable_no_key": unresolvable,
        "resolution_rate_pct": resolution_rate,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    if before_unresolved is not None:
        result["before_unresolved"] = before_unresolved
    if repaired is not None:
        result["repaired_this_run"] = repaired

    logger.info("package_no_repair: %s", json.dumps(
        {k: v for k, v in result.items() if k != "timestamp"},
    ))
    return result
