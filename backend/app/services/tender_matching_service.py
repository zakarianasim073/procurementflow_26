"""TenderMatchingService — extracted from IntelligenceDataService.

Handles tender-to-award matching, lifecycle rebuild, and related
reconciliation logic that was previously embedded in the 5,213-line
IntelligenceDataService monolith.
"""
from __future__ import annotations

import logging
from collections import defaultdict
import re
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4

from sqlalchemy import delete, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.intelligence import (
    APPRecord,
    AwardRecordV2,
    ProcurementLifecycle,
    ProcurementTender,
)

logger = logging.getLogger(__name__)


class TenderMatchingService:
    """Service for matching tenders to awards and rebuilding lifecycle tables."""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ── helpers ───────────────────────────────────────────────────────────

    def _uuid(self) -> str:
        return str(uuid4())

    def _safe_float(self, value: Any) -> float:
        try:
            if value is None:
                return 0.0
            return float(value)
        except Exception:
            return 0.0

    def _valid_package_no(self, value: Any) -> bool:
        text_value = str(value or "").strip()
        return bool(text_value) and not re.fullmatch(r"\d{6,}", text_value)

    def _to_iso_date(self, value: Any) -> Optional[str]:
        if not value:
            return None
        if isinstance(value, str):
            return value[:10] if len(value) >= 10 else value
        return None

    def _coalesce(self, *values: Any) -> Any:
        for v in values:
            if v is not None and v != "":
                return v
        return None

    def _is_credible_npp_row(self, row: Any) -> bool:
        npp = self._safe_float(row.npp_ratio)
        return 0.0 < npp < 5.0

    def _deduplicate_awards(
        self, raw_awards: List[AwardRecordV2], app_tender_ids: set
    ) -> Tuple[List[AwardRecordV2], Dict[str, Any]]:
        """Remove duplicate awards keeping the best-quality row per package."""
        dedup: Dict[str, AwardRecordV2] = {}
        for award in raw_awards:
            tid = award.procurement_tender_id
            if not tid:
                continue
            existing = dedup.get(tid)
            if existing is None:
                dedup[tid] = award
                continue
            # Prefer records with more fields populated
            existing_score = sum(
                1 for f in (existing.contractor_name, existing.amount_bdt, existing.agency_code)
                if f is not None
            )
            new_score = sum(
                1 for f in (award.contractor_name, award.amount_bdt, award.agency_code)
                if f is not None
            )
            if new_score > existing_score:
                dedup[tid] = award
        stats = {"raw_awards": len(raw_awards), "deduped_awards": len(dedup)}
        return list(dedup.values()), stats

    # ── public API ─────────────────────────────────────────────────────────

    async def rebuild_procurement_lifecycle(self) -> Dict[str, int]:
        """Rebuild the procurement_lifecycle table from tenders, awards, and APP records."""
        locked = await self.db.scalar(
            text("SELECT pg_try_advisory_xact_lock(hashtext('rebuild_procurement_lifecycle'))")
        )
        if not locked:
            return {"rows_inserted": 0, "matched_packages": 0, "matched": 0, "app_only": 0, "ec_only": 0, "skipped": "lock_not_acquired"}

        await self.db.execute(delete(ProcurementLifecycle))
        insert_result = await self.db.execute(text("""
            WITH valid_tenders AS (
                SELECT DISTINCT ON (normalized_package_no) *
                FROM procurement_tenders
                WHERE normalized_package_no IS NOT NULL
                  AND normalized_package_no <> ''
                  AND package_no !~ '^[0-9]{6,}$'
                ORDER BY normalized_package_no, updated_at DESC NULLS LAST, created_at DESC NULLS LAST
            ),
            app_latest AS (
                SELECT DISTINCT ON (normalized_package_no)
                    package_no,
                    normalized_package_no,
                    title,
                    pe_office,
                    estimated_cost_bdt
                FROM app_records
                WHERE normalized_package_no IS NOT NULL
                  AND normalized_package_no <> ''
                  AND package_no !~ '^[0-9]{6,}$'
                  AND lower(category) = 'works'
                ORDER BY normalized_package_no, updated_at DESC NULLS LAST, created_at DESC NULLS LAST
            ),
            award_latest AS (
                SELECT DISTINCT ON (normalized_package_no)
                    package_no,
                    normalized_package_no,
                    tender_id,
                    title,
                    contractor_name,
                    amount_bdt,
                    estimated_amount_bdt,
                    award_date,
                    procurement_method,
                    agency_code,
                    district,
                    pe_office
                FROM award_records_v2
                WHERE normalized_package_no IS NOT NULL
                  AND normalized_package_no <> ''
                  AND package_no !~ '^[0-9]{6,}$'
                ORDER BY normalized_package_no, award_date DESC NULLS LAST, updated_at DESC NULLS LAST, created_at DESC NULLS LAST
            ),
            assembled AS (
                SELECT
                    vt.id AS procurement_tender_id,
                    vt.package_no,
                    COALESCE(NULLIF(aw.agency_code, ''), NULLIF(vt.agency_code, '')) AS agency_code,
                    NULLIF(aw.district, '') AS zone_name,
                    COALESCE(NULLIF(aw.title, ''), NULLIF(app.title, ''), NULLIF(vt.title, '')) AS title,
                    COALESCE(app.estimated_cost_bdt, aw.estimated_amount_bdt, 0) AS estimated_cost_bdt,
                    COALESCE(aw.amount_bdt, 0) AS award_amount_bdt,
                    NULLIF(aw.contractor_name, '') AS winner,
                    aw.award_date,
                    COALESCE(NULLIF(aw.procurement_method, ''), NULLIF(vt.procurement_method, '')) AS procurement_method,
                    COALESCE(NULLIF(aw.pe_office, ''), NULLIF(app.pe_office, ''), NULLIF(vt.pe_office, '')) AS pe_office,
                    aw.tender_id,
                    app.package_no IS NOT NULL AS has_app,
                    aw.package_no IS NOT NULL AS has_award
                FROM valid_tenders vt
                JOIN app_latest app ON app.normalized_package_no = vt.normalized_package_no
                LEFT JOIN award_latest aw ON aw.normalized_package_no = vt.normalized_package_no
            )
            INSERT INTO procurement_lifecycle (
                id, package_no, agency_code, zone_name, title,
                estimated_cost_bdt, award_amount_bdt, npp_ratio, winner, award_date,
                procurement_method, pe_office, match_type, data_source, tender_id,
                created_at, updated_at
            )
            SELECT
                md5(package_no),
                package_no,
                agency_code,
                zone_name,
                title,
                estimated_cost_bdt,
                award_amount_bdt,
                CASE
                    WHEN estimated_cost_bdt > 0 AND award_amount_bdt > 0
                    THEN round((award_amount_bdt / estimated_cost_bdt)::numeric, 6)::double precision
                    ELSE 0
                END,
                winner,
                award_date,
                procurement_method,
                pe_office,
                CASE
                    WHEN has_app AND has_award THEN 'package_exact'
                    WHEN has_award THEN 'unmatched_ec'
                    WHEN has_app THEN 'unmatched_app'
                    ELSE 'tender'
                END,
                CASE
                    WHEN has_app AND has_award THEN 'matched'
                    WHEN has_award THEN 'ec_only'
                    WHEN has_app THEN 'app_only'
                    ELSE 'tender'
                END,
                tender_id,
                NOW(),
                NOW()
            FROM assembled
        """))
        stats = (await self.db.execute(text("""
            SELECT
                COUNT(*) AS rows_inserted,
                COUNT(*) FILTER (WHERE data_source = 'matched') AS matched,
                COUNT(*) FILTER (WHERE data_source = 'app_only') AS app_only,
                COUNT(*) FILTER (WHERE data_source = 'ec_only') AS ec_only,
                COUNT(*) FILTER (WHERE data_source = 'tender') AS tender_only
            FROM procurement_lifecycle
        """))).mappings().one()
        await self.db.flush()
        return {
            "rows_inserted": int(stats["rows_inserted"] or insert_result.rowcount or 0),
            "matched_packages": int(stats["matched"] or 0),
            "matched": int(stats["matched"] or 0),
            "app_only": int(stats["app_only"] or 0),
            "ec_only": int(stats["ec_only"] or 0),
            "tender_only": int(stats["tender_only"] or 0),
        }

    async def backfill_live_tender_shell_records(self) -> Dict[str, int]:
        """Create APP shell records for tenders that have awards but no APP record."""
        from app.models.intelligence import APPRecord

        app_cache = {
            row.procurement_tender_id: row
            for row in (await self.db.execute(select(APPRecord))).scalars().all()
        }

        tenders = (
            await self.db.execute(
                select(ProcurementTender, AwardRecordV2)
                .join(AwardRecordV2, AwardRecordV2.procurement_tender_id == ProcurementTender.id)
                .where(ProcurementTender.agency_code.in_(("PWD", "RHD")))
                .order_by(AwardRecordV2.award_date.desc().nullslast())
            )
        ).all()

        created = 0
        seen_tenders: set[str] = set()
        for tender, award in tenders:
            if tender.id in seen_tenders:
                continue
            seen_tenders.add(tender.id)
            if tender.id in app_cache:
                continue

            title = str(tender.title or "")
            award_date = self._to_iso_date(award.award_date) or ""
            looks_current = (
                "2025-2026" in title
                or "25-26" in title
                or award_date >= "2025-01-01"
            )
            if not title or not looks_current:
                continue

            app_record = APPRecord(
                id=self._uuid(),
                procurement_tender_id=tender.id,
                source_tender_id=tender.package_no,
                package_no=tender.package_no,
                title=tender.title,
                estimated_cost_bdt=0.0,
                status="LIVE_TENDER_SHELL",
                published_date=None,
                deadline=None,
                financial_year="2025-2026" if ("2025-2026" in title or "25-26" in title) else None,
                app_code="LIVE_TENDER_SHELL",
                category=tender.procurement_method or "live_tender_shell",
            )
            self.db.add(app_record)
            app_cache[tender.id] = app_record
            created += 1

        await self.db.flush()
        return {"created": created}
