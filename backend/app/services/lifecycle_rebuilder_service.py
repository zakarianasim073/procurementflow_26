"""Lifecycle Rebuilder Service

Fast SQL-based rebuild of procurement_lifecycle from award_records_v2 + app_records.
Creates three categories of lifecycle records:
  - matched: both APP and Award exist for the same tender
  - ec_only: only Award exists (e-contract)
  - app_only: only APP exists (planned tender)

Uses ON CONFLICT for idempotent updates.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.database import get_sync_engine

logger = logging.getLogger(__name__)


class LifecycleRebuilderService:
    """Rebuild procurement_lifecycle from awards and APP records."""

    @staticmethod
    def rebuild() -> Dict[str, Any]:
        """Execute the full lifecycle rebuild via SQL."""
        engine = get_sync_engine()
        with engine.begin() as conn:
            before = conn.execute(
                text("SELECT COUNT(*) FROM procurement_lifecycle")
            ).scalar_one()

            # Delete existing to avoid stale data
            conn.execute(text("DELETE FROM procurement_lifecycle"))

            # Insert matched + ec_only from award_records_v2
            award_inserted = conn.execute(text("""
                INSERT INTO procurement_lifecycle
                (id, package_no, agency_code, zone_name, title, estimated_cost_bdt, award_amount_bdt,
                 npp_ratio, winner, award_date, procurement_method, pe_office, match_type, data_source,
                 tender_id, created_at, updated_at)
                SELECT
                    gen_random_uuid()::text,
                    src.package_no,
                    COALESCE(src.agency_code, pt.agency_code),
                    src.district,
                    COALESCE(src.title, pt.title, ar.title),
                    COALESCE(ar.estimated_cost_bdt, 0),
                    COALESCE(src.amount_bdt, 0),
                    CASE
                        WHEN COALESCE(ar.estimated_cost_bdt, 0) > 0 AND COALESCE(src.amount_bdt, 0) > 0
                        THEN ROUND((src.amount_bdt::numeric / ar.estimated_cost_bdt::numeric), 6)::float
                        ELSE COALESCE(src.npp_ratio, 0)
                    END,
                    src.contractor_name,
                    src.award_date,
                    COALESCE(src.procurement_method, pt.procurement_method),
                    COALESCE(src.pe_office, pt.pe_office),
                    CASE WHEN ar.procurement_tender_id IS NOT NULL THEN 'package_exact' ELSE 'unmatched_ec' END,
                    CASE WHEN ar.procurement_tender_id IS NOT NULL THEN 'matched' ELSE 'ec_only' END,
                    src.tender_id,
                    NOW(),
                    NOW()
                FROM (
                    SELECT DISTINCT ON (package_no, contractor_name, COALESCE(award_date, ''))
                        *
                    FROM award_records_v2
                    WHERE package_no IS NOT NULL AND package_no <> ''
                    ORDER BY package_no, contractor_name, COALESCE(award_date, ''), updated_at DESC NULLS LAST
                ) src
                LEFT JOIN procurement_tenders pt ON pt.id = src.procurement_tender_id
                LEFT JOIN app_records ar ON ar.procurement_tender_id = src.procurement_tender_id
                WHERE src.package_no IS NOT NULL AND src.package_no <> ''
                ON CONFLICT (package_no, winner, award_date) DO NOTHING
            """)).rowcount

            # Insert app_only from app_records without matching award
            app_inserted = conn.execute(text("""
                INSERT INTO procurement_lifecycle
                (id, package_no, agency_code, zone_name, title, estimated_cost_bdt, award_amount_bdt,
                 npp_ratio, winner, award_date, procurement_method, pe_office, match_type, data_source,
                 tender_id, created_at, updated_at)
                SELECT
                    gen_random_uuid()::text,
                    pt.package_no,
                    pt.agency_code,
                    NULL,
                    COALESCE(ar.title, pt.title),
                    COALESCE(ar.estimated_cost_bdt, 0),
                    0,
                    0,
                    NULL,
                    NULL,
                    pt.procurement_method,
                    pt.pe_office,
                    'unmatched_app',
                    'app_only',
                    NULL,
                    NOW(),
                    NOW()
                FROM app_records ar
                JOIN procurement_tenders pt ON pt.id = ar.procurement_tender_id
                WHERE NOT EXISTS (
                    SELECT 1 FROM award_records_v2 aw WHERE aw.procurement_tender_id = pt.id
                )
                ON CONFLICT (package_no, winner, award_date) DO NOTHING
            """)).rowcount

            after = conn.execute(
                text("SELECT COUNT(*) FROM procurement_lifecycle")
            ).scalar_one()

            quality = {
                "with_award_amount": conn.execute(
                    text("SELECT COUNT(*) FROM procurement_lifecycle WHERE award_amount_bdt > 0")
                ).scalar_one(),
                "with_estimate": conn.execute(
                    text("SELECT COUNT(*) FROM procurement_lifecycle WHERE estimated_cost_bdt > 0")
                ).scalar_one(),
                "matched": conn.execute(
                    text("SELECT COUNT(*) FROM procurement_lifecycle WHERE data_source = 'matched'")
                ).scalar_one(),
                "ec_only": conn.execute(
                    text("SELECT COUNT(*) FROM procurement_lifecycle WHERE data_source = 'ec_only'")
                ).scalar_one(),
                "app_only": conn.execute(
                    text("SELECT COUNT(*) FROM procurement_lifecycle WHERE data_source = 'app_only'")
                ).scalar_one(),
            }

        result = {
            "before": before,
            "award_rows_inserted": award_inserted,
            "app_only_rows_inserted": app_inserted,
            "after": after,
            "quality": quality,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        logger.info("Lifecycle rebuild complete: %s", json.dumps(result, indent=2))
        return result


# ── Standalone CLI ────────────────────────────────────────────────────────────

def _cli():
    import logging
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    result = LifecycleRebuilderService.rebuild()
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    _cli()
