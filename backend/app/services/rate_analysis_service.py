"""
Rate Analysis Service
NPP trends, agency intelligence, discount patterns, and award intelligence.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.intelligence_base import IntelligenceBaseService

logger = logging.getLogger(__name__)


class RateAnalysisService(IntelligenceBaseService):
    """
    Rate / NPP / discount analysis and trend computation.
    """

    async def rebuild_aggregate_intelligence(self) -> Dict[str, Any]:
        """Rebuild AgencyIntelligence, ZoneIntelligence, DiscountPattern, AwardIntelligence."""
        from app.models.intelligence import (
            AgencyIntelligence, ZoneIntelligence, DiscountPattern, AwardIntelligence,
            ProcurementLifecycle, AwardRecordV2,
        )
        from sqlalchemy import delete

        await self.session.execute(delete(AgencyIntelligence))
        await self.session.execute(delete(ZoneIntelligence))
        await self.session.execute(delete(DiscountPattern))
        await self.session.execute(delete(AwardIntelligence))

        # Agency intelligence from lifecycle
        stmt = select(
            ProcurementLifecycle.pe_office,
            func.count(ProcurementLifecycle.id),
            func.avg(ProcurementLifecycle.award_amount_bdt),
            func.avg(ProcurementLifecycle.estimated_cost_bdt),
        ).where(ProcurementLifecycle.award_amount_bdt.isnot(None)).group_by(ProcurementLifecycle.pe_office)

        result = await self.session.execute(stmt)
        for pe_office, count, avg_award, avg_estimate in result.all():
            npp = None
            if avg_estimate and avg_estimate > 0:
                npp = avg_award / avg_estimate
            ai = AgencyIntelligence(
                id=self._uuid(),
                agency_code=(pe_office[:20] if pe_office else "UNKNOWN"),
                total_contracts=count,
                total_amount_bdt=float(avg_award or 0) * int(count or 0),
                avg_npp=npp or 0.0,
            )
            self.session.add(ai)

        await self.session.flush()
        return {"rebuilt": True}

    async def get_agency_intelligence(self, agency: str) -> Optional[Dict]:
        """Query AgencyIntelligence."""
        from app.models.intelligence import AgencyIntelligence
        from sqlalchemy import select

        stmt = select(AgencyIntelligence).where(AgencyIntelligence.agency_code == agency)
        result = await self.session.execute(stmt)
        row = result.scalar_one_or_none()
        if not row:
            return None
        return {
            "agency": row.agency_code,
            "total_awards": row.total_contracts,
            "avg_npp": row.avg_npp,
            "last_updated": row.updated_at.isoformat() if row.updated_at else None,
        }

    async def get_npp_trends(self, months: int = 12) -> List[Dict]:
        """Monthly NPP trend query."""
        from app.models.intelligence import ProcurementLifecycle
        from sqlalchemy import select, func, extract

        stmt = (
            select(
                extract("year", ProcurementLifecycle.award_date).label("year"),
                extract("month", ProcurementLifecycle.award_date).label("month"),
                func.avg(ProcurementLifecycle.award_amount_bdt / ProcurementLifecycle.estimated_cost_bdt),
                func.count(ProcurementLifecycle.id),
            )
            .where(ProcurementLifecycle.award_date.isnot(None))
            .where(ProcurementLifecycle.estimated_cost_bdt.isnot(None))
            .where(ProcurementLifecycle.estimated_cost_bdt > 0)
            .group_by("year", "month")
            .order_by("year", "month")
        )
        result = await self.session.execute(stmt)
        rows = []
        for year, month, avg_npp, count in result.all():
            rows.append({
                "year": int(year) if year else None,
                "month": int(month) if month else None,
                "avg_npp": round(avg_npp or 0, 4),
                "count": count,
            })
        return rows

    async def get_zone_intelligence(self, zone: str) -> Optional[Dict]:
        """Query ZoneIntelligence."""
        from app.models.intelligence import ZoneIntelligence
        from sqlalchemy import select

        stmt = select(ZoneIntelligence).where(ZoneIntelligence.zone_name == zone)
        result = await self.session.execute(stmt)
        row = result.scalar_one_or_none()
        if not row:
            return None
        return {
            "zone": row.zone_name,
            "total_awards": row.total_contracts,
            "avg_npp": row.avg_npp,
            "last_updated": row.updated_at.isoformat() if row.updated_at else None,
        }

    async def get_discount_patterns(self, limit: int = 100) -> List[Dict]:
        """Query DiscountPattern."""
        from app.models.intelligence import DiscountPattern
        from sqlalchemy import select

        stmt = select(DiscountPattern).limit(limit)
        result = await self.session.execute(stmt)
        return [
            {
                "id": r.id,
                "agency": r.agency_code,
                "zone": r.zone_name,
                "avg_npp": r.avg_npp,
                "sample_size": r.sample_size,
                "last_updated": r.updated_at.isoformat() if r.updated_at else None,
            }
            for r in result.scalars().all()
        ]

    async def get_award_trends(self, quarters: int = 8) -> List[Dict]:
        """Quarterly AwardIntelligence query."""
        from app.models.intelligence import AwardRecordV2
        from sqlalchemy import select, func, extract

        stmt = (
            select(
                extract("year", AwardRecordV2.award_date).label("year"),
                extract("quarter", AwardRecordV2.award_date).label("quarter"),
                func.avg(AwardRecordV2.amount_bdt),
                func.count(AwardRecordV2.id),
            )
            .where(AwardRecordV2.award_date.isnot(None))
            .group_by("year", "quarter")
            .order_by("year", "quarter")
        )
        result = await self.session.execute(stmt)
        rows = []
        for year, quarter, avg_amount, count in result.all():
            rows.append({
                "year": int(year) if year else None,
                "quarter": int(quarter) if quarter else None,
                "avg_awarded_amount": round(avg_amount or 0, 2),
                "count": count,
            })
        return rows
