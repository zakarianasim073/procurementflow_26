"""
APP / NOA Matching Service
Handles APP record ingestion, NOA award ingestion, live tender ingestion,
and the core package-number matching algorithm between APP/NOA/Live data.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from sqlalchemy import and_, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.intelligence_base import IntelligenceBaseService

logger = logging.getLogger(__name__)


class APPNOAMatchingService(IntelligenceBaseService):
    """
    Ingestion and matching for APP plans, NOA awards, and live tenders.
    Central responsibility: normalized package_no matching across sources.
    """

    async def import_existing_json_data(self, progress=None) -> Dict[str, Any]:
        """Orchestrator: scan JSON roots and route to sub-importers."""
        from app.models.intelligence import ImportProgress
        progress = progress or ImportProgress()
        progress.state = "running"
        progress.started = True

        summary = {"scanned": 0, "imported": 0, "errors": 0, "files": []}

        for root in self._legacy_roots:
            if not root.exists():
                continue
            for json_file in self._iter_json_files(root):
                progress.current_file = json_file.name
                try:
                    with open(json_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    summary["scanned"] += 1
                    fname = json_file.name.lower()
                    if "app" in fname or "structure" in fname:
                        await self.import_app_structure_from_json(data)
                    elif "award" in fname or "noa" in fname:
                        await self.import_awards_from_json(data)
                    elif "live" in fname or "tender" in fname:
                        await self.import_live_tenders_from_json(data)
                    elif "lifecycle" in fname or "flat" in fname:
                        await self.import_lifecycle_from_json(data)
                    elif "contractor" in fname:
                        await self.import_contractors_from_json(data)
                    elif "eexperience" in fname or "execution" in fname:
                        await self.import_eexperience_from_json(data)
                    summary["imported"] += 1
                    summary["files"].append(json_file.name)
                except Exception as e:
                    summary["errors"] += 1
                    logger.warning("JSON import failed for %s: %s", json_file, e)

        progress.state = "completed"
        progress.summary = summary
        return summary

    async def ingest_live_tender_notice(self, data: Dict) -> Dict[str, Any]:
        """Ingest a single live tender notice."""
        from app.models.intelligence import ProcurementTender, APPRecord, LiveTenderSource
        package_no = self.normalize_package_no(data.get("package_no"))
        if not package_no:
            return {"success": False, "error": "no package_no"}

        tender, created = await self._get_or_create_tender(package_no, data)
        app_record = APPRecord(
            id=self._uuid(),
            procurement_tender_id=tender.id,
            source_tender_id=package_no,
            package_no=package_no,
            title=data.get("title", data.get("tender_title", ""))[:500],
            pe_office=data.get("procuring_entity", data.get("department", ""))[:255],
            estimated_cost_bdt=self._safe_float(data.get("estimated_cost")),
            deadline=self._to_iso_date(data.get("deadline")),
            status=data.get("status", "live"),
            created_at=datetime.now(timezone.utc),
        )
        self.session.add(app_record)
        await self.session.flush()
        return {"success": True, "tender_id": tender.id, "created": created}

    async def ingest_app_plan_record(self, data: Dict) -> Dict[str, Any]:
        """Ingest an APP plan record."""
        from app.models.intelligence import ProcurementTender, APPRecord
        package_no = self.normalize_package_no(data.get("package_no"))
        if not package_no:
            return {"success": False, "error": "no package_no"}

        tender, _ = await self._get_or_create_tender(package_no, data)
        app_record = APPRecord(
            id=self._uuid(),
            procurement_tender_id=tender.id,
            source_tender_id=package_no,
            package_no=package_no,
            title=data.get("title", "")[:500],
            pe_office=data.get("procuring_entity", "")[:255],
            estimated_cost_bdt=self._safe_float(data.get("estimated_cost")),
            deadline=self._to_iso_date(data.get("deadline")),
            status="app_planned",
            created_at=datetime.now(timezone.utc),
        )
        self.session.add(app_record)
        await self.session.flush()
        return {"success": True, "tender_id": tender.id}

    async def ingest_noa_award_notice(self, data: Dict) -> Dict[str, Any]:
        """Ingest an NOA award notice."""
        from app.models.intelligence import AwardRecordV2, ProcurementTender
        package_no = self.normalize_package_no(data.get("package_no"))
        if not package_no:
            return {"success": False, "error": "no package_no"}

        tender, _ = await self._get_or_create_tender(package_no, data)
        award = AwardRecordV2(
            id=self._uuid(),
            procurement_tender_id=tender.id,
            source_tender_id=package_no,
            package_no=package_no,
            tender_id=self._numeric_tender_id(data.get("tender_id")),
            title=data.get("title", "")[:500],
            pe_office=data.get("procuring_entity", "")[:255],
            contractor_name=data.get("contractor_name", "")[:255],
            amount_bdt=self._safe_float(data.get("awarded_amount")),
            award_date=self._to_iso_date(data.get("award_date")),
            npp_ratio=self._safe_float(data.get("npp")),
            created_at=datetime.now(timezone.utc),
        )
        self.session.add(award)
        await self.session.flush()
        return {"success": True, "award_id": award.id}

    async def import_live_tenders_from_json(self, data: List[Dict]) -> Dict[str, Any]:
        """Bulk import live tenders from JSON."""
        imported = 0
        for item in data:
            result = await self.ingest_live_tender_notice(item)
            if result.get("success"):
                imported += 1
        return {"imported": imported, "total": len(data)}

    async def import_awards_from_json(self, data: List[Dict]) -> Dict[str, Any]:
        """Bulk import awards from JSON."""
        imported = 0
        for item in data:
            result = await self.ingest_noa_award_notice(item)
            if result.get("success"):
                imported += 1
        return {"imported": imported, "total": len(data)}

    async def import_app_structure_from_json(self, data: List[Dict]) -> Dict[str, Any]:
        """Bulk import APP structure from JSON."""
        imported = 0
        for item in data:
            result = await self.ingest_app_plan_record(item)
            if result.get("success"):
                imported += 1
        return {"imported": imported, "total": len(data)}

    async def reconcile_awards_to_app_records(self, progress=None) -> Dict[str, Any]:
        """
        Core matching algorithm: link awards to APP records by package_no + title similarity.
        """
        from app.models.intelligence import AwardRecordV2, APPRecord, ProcurementTender
        from sqlalchemy import select

        result = await self.session.execute(select(AwardRecordV2))
        awards = result.scalars().all()

        matched = 0
        for award in awards:
            if not award.package_no:
                continue
            stmt = select(APPRecord).where(
                and_(APPRecord.package_no == award.package_no, APPRecord.title.isnot(None))
            )
            app_result = await self.session.execute(stmt)
            app_records = app_result.scalars().all()

            best_match = None
            best_score = 0.0
            for app in app_records:
                score = self._contractor_match_score(award.title or "", app.title or "")
                if score > best_score and score > 0.7:
                    best_score = score
                    best_match = app

            if best_match:
                award.procurement_tender_id = best_match.procurement_tender_id
                matched += 1
            if progress:
                progress.current_file_records = len(awards)
                progress.current_file_imported = matched

        await self.session.flush()
        return {"matched": matched, "total_awards": len(awards)}

    async def backfill_live_tender_shell_records(self) -> Dict[str, Any]:
        """Create synthetic APPRecord shells for live tenders that lack APP data."""
        from app.models.intelligence import ProcurementTender, APPRecord
        from sqlalchemy import select

        stmt = select(ProcurementTender).outerjoin(APPRecord, APPRecord.procurement_tender_id == ProcurementTender.id).where(APPRecord.id.is_(None))
        result = await self.session.execute(stmt)
        tenders = result.scalars().all()

        created = 0
        for tender in tenders:
            app = APPRecord(
                id=self._uuid(),
                procurement_tender_id=tender.id,
                source_tender_id=tender.package_no or "",
                package_no=tender.package_no or "",
                title=tender.title or "",
                pe_office=tender.pe_office or "",
                status="live_shell",
                created_at=datetime.now(timezone.utc),
            )
            self.session.add(app)
            created += 1

        await self.session.flush()
        return {"created": created}

    async def list_awards_for_agent(self, agency: str = "", limit: int = 100) -> List[Dict]:
        """Award listing with APP estimate join."""
        from app.models.intelligence import AwardRecordV2, APPRecord
        from sqlalchemy import select

        stmt = (
            select(AwardRecordV2, APPRecord)
            .outerjoin(APPRecord, APPRecord.package_no == AwardRecordV2.package_no)
            .limit(max(1, min(int(limit or 100), 500)))
        )
        if agency:
            stmt = stmt.where(AwardRecordV2.agency_code.ilike(f"%{agency}%"))
        result = await self.session.execute(stmt)
        rows = []
        for award, app in result.all():
            rows.append({
                "award_id": award.id,
                "package_no": award.package_no,
                "title": award.title,
                "contractor": award.contractor_name,
                "awarded_amount": award.amount_bdt,
                "estimated_amount": app.estimated_cost_bdt if app else None,
                "award_date": award.award_date,
            })
        return rows

    async def get_award_data_quality_stats(self) -> Dict[str, Any]:
        """Deduplication stats on awards."""
        from app.models.intelligence import AwardRecordV2
        from sqlalchemy import select, func

        total = await self.session.execute(select(func.count(AwardRecordV2.id)))
        total_count = total.scalar()

        pkg = await self.session.execute(select(func.count(func.distinct(AwardRecordV2.package_no))))
        distinct_packages = pkg.scalar()

        return {
            "total_awards": total_count,
            "distinct_packages": distinct_packages,
            "duplicates": total_count - distinct_packages if total_count and distinct_packages else 0,
        }

    async def reconcile_award_package_mapping_from_json(self, flat_path, progress=None):
        """Stub for award package mapping reconciliation from JSON."""
        return 0

    # ── Internal helpers ─────────────────────────────────────────────────

    async def _get_or_create_tender(self, package_no: str, data: Dict) -> tuple:
        from app.models.intelligence import ProcurementTender
        from sqlalchemy import select

        stmt = select(ProcurementTender).where(ProcurementTender.package_no == package_no)
        result = await self.session.execute(stmt)
        existing = result.scalar_one_or_none()
        if existing:
            return existing, False

        tender = ProcurementTender(
            id=self._uuid(),
            package_no=package_no,
            title=data.get("title", "")[:500],
            pe_office=data.get("procuring_entity", "")[:255],
            procurement_method=data.get("procurement_method", "")[:100],
            match_type=data.get("status", "new"),
            created_at=datetime.now(timezone.utc),
        )
        self.session.add(tender)
        await self.session.flush()
        return tender, True
