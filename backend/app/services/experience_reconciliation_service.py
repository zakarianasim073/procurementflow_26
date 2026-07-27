"""
Experience Reconciliation Service
Handles eExperience / eCMS / EContractExecution import, query, and tender linking.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.intelligence_base import IntelligenceBaseService

logger = logging.getLogger(__name__)


class ExperienceReconciliationService(IntelligenceBaseService):
    """
    eExperience / eCMS / EContractExecution reconciliation and analytics.
    """

    async def import_eexperience_from_json(self, data: List[Dict]) -> Dict[str, Any]:
        """Import eExperience JSON into EContractExecution."""
        from app.models.intelligence import EContractExecution
        imported = 0
        for item in data:
            package_no = self.normalize_package_no(item.get("package_no"))
            if not package_no:
                continue
            execution = EContractExecution(
                id=self._uuid(),
                package_no=package_no,
                contractor_name=item.get("contractor_name", "")[:255],
                contract_value=self._safe_float(item.get("contract_value")),
                physical_progress_pct=self._safe_float(item.get("physical_progress")),
                financial_progress_pct=self._safe_float(item.get("financial_progress")),
                start_date=self._to_iso_date(item.get("start_date")),
                completion_date=self._to_iso_date(item.get("completion_date")),
                status=item.get("status", "ongoing"),
                created_at=datetime.now(timezone.utc),
            )
            self.session.add(execution)
            imported += 1
        await self.session.flush()
        return {"imported": imported, "total": len(data)}

    async def import_experience_to_dedicated_tables(self, data: Dict) -> Dict[str, Any]:
        """Import all_completed.json / all_ongoing.json into EExperienceCompleted / ECMSongoing."""
        from app.models.intelligence import EExperienceCompleted, ECMSongoing
        completed = data.get("completed", [])
        ongoing = data.get("ongoing", [])

        imported_completed = 0
        for item in completed:
            package_no = self.normalize_package_no(item.get("package_no", ""))
            if not package_no:
                continue
            rec = EExperienceCompleted(
                id=self._uuid(),
                package_no=package_no,
                contractor_name=item.get("contractor_name", "")[:255],
                contract_value=self._safe_float(item.get("contract_value")),
                completion_date=self._to_iso_date(item.get("completion_date")),
                created_at=datetime.now(timezone.utc),
            )
            self.session.add(rec)
            imported_completed += 1

        imported_ongoing = 0
        for item in ongoing:
            package_no = self.normalize_package_no(item.get("package_no", ""))
            if not package_no:
                continue
            rec = ECMSongoing(
                id=self._uuid(),
                package_no=package_no,
                contractor_name=item.get("contractor_name", "")[:255],
                contract_value=self._safe_float(item.get("contract_value")),
                start_date=self._to_iso_date(item.get("start_date")),
                created_at=datetime.now(timezone.utc),
            )
            self.session.add(rec)
            imported_ongoing += 1

        await self.session.flush()
        return {"imported_completed": imported_completed, "imported_ongoing": imported_ongoing}

    async def query_eexperience(self, limit: int = 100, filters: Dict = None) -> List[Dict]:
        """EContractExecution query."""
        from app.models.intelligence import EContractExecution
        from sqlalchemy import select

        stmt = select(EContractExecution).limit(limit)
        if filters:
            if filters.get("package_no"):
                stmt = stmt.where(EContractExecution.package_no == filters["package_no"])
            if filters.get("contractor"):
                stmt = stmt.where(EContractExecution.contractor_name.ilike(f"%{filters['contractor']}%"))
            if filters.get("status"):
                stmt = stmt.where(EContractExecution.status == filters["status"])
        result = await self.session.execute(stmt)
        return [self._execution_to_dict(r) for r in result.scalars().all()]

    async def get_eexperience_stats(self) -> Dict[str, Any]:
        """eExperience aggregates."""
        from app.models.intelligence import EContractExecution
        from sqlalchemy import select, func

        total = await self.session.execute(select(func.count(EContractExecution.id)))
        total_count = total.scalar()

        avg_physical = await self.session.execute(select(func.avg(EContractExecution.physical_progress_pct)))
        avg_financial = await self.session.execute(select(func.avg(EContractExecution.financial_progress_pct)))

        return {
            "total": total_count,
            "avg_physical_progress": round(avg_physical.scalar() or 0, 2),
            "avg_financial_progress": round(avg_financial.scalar() or 0, 2),
        }

    async def get_contractor_performance(self, contractor_name: str) -> Dict[str, Any]:
        """Contractor performance from eExperience."""
        from app.models.intelligence import EContractExecution
        from sqlalchemy import select, func

        stmt = select(
            func.count(EContractExecution.id),
            func.avg(EContractExecution.physical_progress_pct),
            func.avg(EContractExecution.financial_progress_pct),
            func.sum(EContractExecution.contract_value),
        ).where(EContractExecution.contractor_name.ilike(f"%{contractor_name}%"))

        result = await self.session.execute(stmt)
        row = result.first()
        return {
            "contractor": contractor_name,
            "total_projects": row[0] or 0,
            "avg_physical_progress": round(row[1] or 0, 2),
            "avg_financial_progress": round(row[2] or 0, 2),
            "total_value": row[3] or 0,
        }

    async def get_rate_quoted_analysis(self, limit: int = 100) -> List[Dict]:
        """Award vs completed value variance analysis."""
        from app.models.intelligence import AwardRecordV2, EExperienceCompleted
        from sqlalchemy import select

        stmt = select(AwardRecordV2, EExperienceCompleted).join(
            EExperienceCompleted, AwardRecordV2.package_no == EExperienceCompleted.package_no
        ).limit(limit)
        result = await self.session.execute(stmt)
        rows = []
        for award, completed in result.all():
            variance = None
            if award.amount_bdt and completed.contract_value:
                variance = round(((completed.contract_value - award.amount_bdt) / award.amount_bdt) * 100, 2)
            rows.append({
                "package_no": award.package_no,
                "awarded_amount": award.amount_bdt,
                "completed_value": completed.contract_value,
                "variance_pct": variance,
            })
        return rows

    async def reconcile_execution_to_lifecycle(self) -> Dict[str, Any]:
        """Link EContractExecution to ProcurementTender."""
        from app.models.intelligence import EContractExecution, ProcurementTender
        from sqlalchemy import select

        stmt = select(EContractExecution).where(EContractExecution.procurement_tender_id.is_(None))
        result = await self.session.execute(stmt)
        executions = result.scalars().all()

        linked = 0
        for execution in executions:
            tender_stmt = select(ProcurementTender).where(ProcurementTender.package_no == execution.package_no)
            tender_result = await self.session.execute(tender_stmt)
            tender = tender_result.scalar_one_or_none()
            if tender:
                execution.procurement_tender_id = tender.id
                linked += 1

        await self.session.flush()
        return {"linked": linked}

    async def reconcile_eexperience_to_tender(self) -> Dict[str, Any]:
        """Link EExperienceCompleted + ECMSongoing to ProcurementTender."""
        from app.models.intelligence import EExperienceCompleted, ECMSongoing, ProcurementTender
        from sqlalchemy import select

        linked = 0
        for model in (EExperienceCompleted, ECMSongoing):
            stmt = select(model).where(model.procurement_tender_id.is_(None))
            result = await self.session.execute(stmt)
            records = result.scalars().all()
            for rec in records:
                tender_stmt = select(ProcurementTender).where(ProcurementTender.package_no == rec.package_no)
                tender_result = await self.session.execute(tender_stmt)
                tender = tender_result.scalar_one_or_none()
                if tender:
                    rec.procurement_tender_id = tender.id
                    linked += 1

        await self.session.flush()
        return {"linked": linked}

    async def get_execution_intelligence(self) -> Dict[str, Any]:
        """Dashboard execution summary."""
        stats = await self.get_eexperience_stats()
        return {
            "success": True,
            "execution": stats,
        }

    async def query_completed_executions(self, limit: int = 100) -> List[Dict]:
        """EExperienceCompleted query."""
        from app.models.intelligence import EExperienceCompleted
        from sqlalchemy import select

        stmt = select(EExperienceCompleted).limit(limit)
        result = await self.session.execute(stmt)
        return [self._execution_to_dict(r) for r in result.scalars().all()]

    async def query_ongoing_executions(self, limit: int = 100) -> List[Dict]:
        """ECMSongoing query."""
        from app.models.intelligence import ECMSongoing
        from sqlalchemy import select

        stmt = select(ECMSongoing).limit(limit)
        result = await self.session.execute(stmt)
        return [self._execution_to_dict(r) for r in result.scalars().all()]

    # ── Internal helpers ─────────────────────────────────────────────────

    def _execution_to_dict(self, r) -> Dict:
        return {
            "id": r.id,
            "package_no": r.package_no,
            "contractor_name": r.contractor_name,
            "contract_value": r.contract_value,
            "physical_progress_pct": getattr(r, "physical_progress_pct", None),
            "financial_progress_pct": getattr(r, "financial_progress_pct", None),
            "start_date": r.start_date,
            "completion_date": getattr(r, "completion_date", None),
            "status": getattr(r, "status", None),
        }
