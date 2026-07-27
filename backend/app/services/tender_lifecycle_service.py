"""
Tender Lifecycle Service
Manages ProcurementLifecycle records, works-record queries, and live-tender search.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import and_, func, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.intelligence_base import IntelligenceBaseService

logger = logging.getLogger(__name__)


class TenderLifecycleService(IntelligenceBaseService):
    """
    ProcurementLifecycle management, works-record building, and tender search.
    """

    async def import_lifecycle_from_json(self, data: List[Dict]) -> Dict[str, Any]:
        """Import flat lifecycle JSON into ProcurementLifecycle."""
        from app.models.intelligence import ProcurementLifecycle
        imported = 0
        for item in data:
            package_no = self.normalize_package_no(item.get("package_no"))
            if not package_no:
                continue
            lifecycle = ProcurementLifecycle(
                id=self._uuid(),
                package_no=package_no,
                title=item.get("title", "")[:500],
                pe_office=item.get("procuring_entity", "")[:255],
                estimated_cost_bdt=self._safe_float(item.get("estimated_cost")),
                award_amount_bdt=self._safe_float(item.get("awarded_amount")),
                award_date=self._to_iso_date(item.get("award_date")),
                procurement_method=item.get("procurement_method", "")[:100],
                match_type=item.get("status", "unknown"),
                created_at=datetime.now(timezone.utc),
            )
            self.session.add(lifecycle)
            imported += 1
        await self.session.flush()
        return {"imported": imported, "total": len(data)}

    async def import_matched_lifecycle_from_json(self, data: List[Dict]) -> Dict[str, Any]:
        """Import all_matches.json into ProcurementLifecycle."""
        return await self.import_lifecycle_from_json(data)

    async def rebuild_procurement_lifecycle(self) -> Dict[str, Any]:
        """Rebuild ProcurementLifecycle from tenders + awards + APP."""
        from app.models.intelligence import ProcurementLifecycle, ProcurementTender, AwardRecordV2, APPRecord
        from sqlalchemy import delete
        from app.services.runtime_guards import distributed_lock

        async with distributed_lock("rebuild_procurement_lifecycle", ttl=1800) as acquired:
            if not acquired:
                return {"rebuilt": 0, "skipped": "lock_not_acquired"}

            # Clear existing
            await self.session.execute(delete(ProcurementLifecycle))

            stmt = select(ProcurementTender)
            result = await self.session.execute(stmt)
            tenders = result.scalars().all()

            rebuilt = 0
            for tender in tenders:
                award_stmt = select(AwardRecordV2).where(AwardRecordV2.package_no == tender.package_no).order_by(AwardRecordV2.award_date.desc().nullslast())
                award_result = await self.session.execute(award_stmt)
                award = award_result.scalars().first()

                app_stmt = select(APPRecord).where(APPRecord.package_no == tender.package_no).order_by(APPRecord.created_at.desc())
                app_result = await self.session.execute(app_stmt)
                app = app_result.scalars().first()

                lifecycle = ProcurementLifecycle(
                    id=self._uuid(),
                    package_no=tender.package_no,
                    title=tender.title or (app.title if app else ""),
                    pe_office=tender.pe_office or (app.pe_office if app else ""),
                    estimated_cost_bdt=app.estimated_cost_bdt if app else None,
                    award_amount_bdt=award.amount_bdt if award else None,
                    award_date=award.award_date if award else None,
                    procurement_method=tender.procurement_method,
                    match_type="awarded" if award else ("app" if app else "tender_only"),
                    created_at=datetime.now(timezone.utc),
                )
                self.session.add(lifecycle)
                rebuilt += 1

            await self.session.flush()
            return {"rebuilt": rebuilt}

    async def query_lifecycle(self, limit: int = 5000, filters: Dict = None) -> Dict[str, Any]:
        """Filtered lifecycle query with pagination support."""
        from app.models.intelligence import ProcurementLifecycle
        from sqlalchemy import select
        from app.services.runtime_guards import cache_get, cache_set

        cache_key = f"lifecycle:{limit}:{filters or {}}"
        cached = await cache_get(cache_key)
        if cached is not None:
            return cached

        stmt = select(ProcurementLifecycle).order_by(ProcurementLifecycle.award_date.desc().nullslast())
        if filters:
            if filters.get("package_no"):
                stmt = stmt.where(ProcurementLifecycle.package_no == filters["package_no"])
            if filters.get("agency"):
                stmt = stmt.where(ProcurementLifecycle.pe_office.ilike(f"%{filters['agency']}%"))
            if filters.get("status"):
                stmt = stmt.where(ProcurementLifecycle.match_type == filters["status"])

        stmt = stmt.limit(limit)
        result = await self.session.execute(stmt)
        rows = result.scalars().all()
        payload = {
            "total": len(rows),
            "records": [
                {
                    "package_no": r.package_no,
                    "title": r.title,
                    "pe_office": r.pe_office,
                    "estimated_cost_bdt": r.estimated_cost_bdt,
                    "award_amount_bdt": r.award_amount_bdt,
                    "award_date": r.award_date,
                    "match_type": r.match_type,
                    "procurement_method": r.procurement_method,
                }
                for r in rows
            ],
        }
        await cache_set(cache_key, payload, ttl=120)
        return payload

    async def query_works_records(self, limit: int = 5000, filters: Dict = None) -> List[Dict]:
        """Rich composite: joins lifecycle + tender + APP + live + award + opening report."""
        from app.models.intelligence import ProcurementLifecycle, ProcurementTender, APPRecord, AwardRecordV2, LiveTenderSource, OpeningReport
        from sqlalchemy import select

        stmt = select(ProcurementLifecycle).limit(limit)
        result = await self.session.execute(stmt)
        lifecycles = result.scalars().all()

        records = []
        for lc in lifecycles:
            tender_stmt = select(ProcurementTender).where(ProcurementTender.package_no == lc.package_no)
            tender_result = await self.session.execute(tender_stmt)
            tender = tender_result.scalar_one_or_none()

            award_stmt = select(AwardRecordV2).where(AwardRecordV2.package_no == lc.package_no)
            award_result = await self.session.execute(award_stmt)
            award = award_result.scalar_one_or_none()

            records.append({
                "package_no": lc.package_no,
                "title": lc.title,
                "pe_office": lc.pe_office,
                "estimated_cost": lc.estimated_cost_bdt,
                "award_amount": lc.award_amount_bdt,
                "award_date": lc.award_date,
                "contractor": award.contractor_name if award else None,
                "npp": award.npp_ratio if award else None,
                "status": lc.match_type,
                "tender_id": tender.id if tender else None,
            })
        return records

    async def get_lifecycle_stats(self) -> Dict[str, Any]:
        """Lifecycle aggregate stats."""
        from app.models.intelligence import ProcurementLifecycle
        from sqlalchemy import select, func

        total = await self.session.execute(select(func.count(ProcurementLifecycle.id)))
        total_count = total.scalar()

        awarded = await self.session.execute(
            select(func.count(ProcurementLifecycle.id)).where(ProcurementLifecycle.match_type == "awarded")
        )
        awarded_count = awarded.scalar()

        return {
            "total": total_count,
            "awarded": awarded_count,
            "pending": total_count - awarded_count if total_count else 0,
        }

    async def get_live_tender_stats(self) -> Dict[str, Any]:
        """Live tender summary."""
        from app.models.intelligence import LiveTenderSource
        from sqlalchemy import select, func

        total = await self.session.execute(select(func.count(LiveTenderSource.id)))
        return {"total_live_tenders": total.scalar()}

    async def search_live_tenders(self, query: str = "", limit: int = 50) -> List[Dict]:
        """Live tender dashboard search with department filtering."""
        from app.models.intelligence import LiveTenderSource, ProcurementTender
        from sqlalchemy import select, or_

        stmt = (
            select(LiveTenderSource, ProcurementTender)
            .join(ProcurementTender, ProcurementTender.id == LiveTenderSource.procurement_tender_id)
            .limit(limit)
        )
        if query:
            q = f"%{query}%"
            stmt = stmt.where(
                or_(
                    LiveTenderSource.title.ilike(q),
                    LiveTenderSource.procuring_entity.ilike(q),
                    ProcurementTender.package_no.ilike(q),
                )
            )
        result = await self.session.execute(stmt)
        rows = result.all()
        return [
            {
                "id": live.id,
                "package_no": tender.package_no,
                "source_tender_id": live.source_tender_id,
                "title": live.title or tender.title,
                "procuring_entity": live.procuring_entity,
                "estimated_cost": live.estimated_value_bdt,
                "deadline": live.deadline,
                "status": live.status,
            }
            for live, tender in rows
        ]

    async def backfill_tender_regimes(self) -> Dict[str, Any]:
        """Backfill regime column on legacy tenders table."""
        from app.models.intelligence import ProcurementTender
        from sqlalchemy import select, update

        stmt = select(ProcurementTender).where(ProcurementTender.regime.is_(None))
        result = await self.session.execute(stmt)
        tenders = result.scalars().all()

        updated = 0
        for tender in tenders:
            regime = self._guess_agency_code({"procuring_entity": tender.pe_office, "title": tender.title})
            if regime:
                tender.regime = regime
                updated += 1

        await self.session.flush()
        return {"updated": updated}
