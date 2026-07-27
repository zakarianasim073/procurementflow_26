"""CompetitorService â€“ domain service extracted from IntelligenceDataService monolith."""
from __future__ import annotations

import json
import logging
import os
import re
from html import unescape
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone, date
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional
from uuid import uuid4

from sqlalchemy import and_, case, delete, func, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.agency_extractor import extract_agency_with_confidence
from app.services.intelligence_base import IntelligenceBaseService

logger = logging.getLogger(__name__)

MIN_CREDIBLE_NPP = 0.05
MAX_CREDIBLE_NPP = 1.5
MIN_CREDIBLE_ESTIMATE_BDT = 1000.0
MIN_CREDIBLE_AWARD_BDT = 1000.0


class CompetitorService(IntelligenceBaseService):
    """Domain service for competitor operations."""

    def __init__(self, db: AsyncSession):
        super().__init__(db)
        self.db = db
        self._batch_size = max(int(os.getenv("INTEL_IMPORT_BATCH_SIZE", "500")), 50)

    @staticmethod
    def _row_to_dict(row) -> Dict[str, Any]:
        if row is None:
            return {}
        payload: Dict[str, Any] = {}
        for col in row.__table__.columns:
            val = getattr(row, col.name)
            if isinstance(val, datetime):
                val = val.isoformat()
            payload[col.name] = val
        return payload
    async def get_agency_intelligence(self, agency_code: Optional[str] = None) -> List[Dict[str, Any]]:
        from app.models.intelligence import AgencyIntelligence

        stmt = select(AgencyIntelligence)
        if agency_code:
            stmt = stmt.where(AgencyIntelligence.agency_code == agency_code)
        stmt = stmt.order_by(AgencyIntelligence.total_amount_bdt.desc())
        result = await self.db.execute(stmt)
        return [self._row_to_dict(r) for r in result.scalars().all()]
    async def get_discount_patterns(
        self,
        agency: Optional[str] = None,
        zone: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        from app.models.intelligence import DiscountPattern

        conditions = []
        if agency:
            conditions.append(DiscountPattern.agency_code == agency)
        if zone:
            conditions.append(DiscountPattern.zone_name.ilike(f"%{zone}%"))
        where_clause = and_(*conditions) if conditions else text("1=1")
        result = await self.db.execute(
            select(DiscountPattern)
            .where(where_clause)
            .order_by(DiscountPattern.sample_size.desc(), DiscountPattern.agency_code.asc())
        )
        return [self._row_to_dict(r) for r in result.scalars().all()]
    async def get_npp_trends(self, months: int = 12) -> List[Dict[str, Any]]:
        from app.models.intelligence import ProcurementLifecycle as PL

        month_expr = func.substr(PL.award_date, 1, 7)
        result = await self.db.execute(
            select(
                PL.agency_code,
                month_expr.label("month"),
                func.avg(PL.npp_ratio).label("avg_npp"),
                func.count(PL.id).label("count"),
            )
            .where(
                and_(
                    PL.npp_ratio >= MIN_CREDIBLE_NPP,
                    PL.npp_ratio <= MAX_CREDIBLE_NPP,
                    PL.estimated_cost_bdt >= MIN_CREDIBLE_ESTIMATE_BDT,
                    PL.award_amount_bdt >= MIN_CREDIBLE_AWARD_BDT,
                    PL.match_type.in_(("package_exact", "title_similarity")),
                    PL.data_source == "matched",
                    PL.award_date.is_not(None),
                )
            )
            .group_by(PL.agency_code, month_expr)
            .order_by(month_expr.asc(), PL.agency_code.asc())
        )
        rows = [
            {
                "agency_code": r[0],
                "agency": r[0],
                "month": r[1],
                "avg_npp": round(float(r[2] or 0), 4),
                "count": int(r[3] or 0),
            }
            for r in result.all()
        ]
        return rows[-months:] if months and len(rows) > months else rows
    async def get_zone_intelligence(self) -> List[Dict[str, Any]]:
        from app.models.intelligence import ZoneIntelligence

        result = await self.db.execute(
            select(ZoneIntelligence).order_by(ZoneIntelligence.total_amount_bdt.desc())
        )
        return [self._row_to_dict(r) for r in result.scalars().all()]
