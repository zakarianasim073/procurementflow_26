"""RateAnalysisService — domain service for element-wise rate analysis with market prices and profit margin.

Wraps `rate_analysis_engine` for use through the intelligence domain service layer.
Provides element breakdown, market price comparison, and profit margin analysis
for BOQ items with recognized SOR compositions.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.intelligence_base import IntelligenceBaseService
from app.services.rate_analysis_engine import analyze_item, analyze_boq_items

logger = logging.getLogger(__name__)


class RateAnalysisService(IntelligenceBaseService):
    """Domain service for element-wise rate analysis."""

    def __init__(self, db: AsyncSession):
        super().__init__(db)
        self.db = db

    async def analyze(
        self,
        boq_items: List[Dict[str, Any]],
        zone: str = "A",
    ) -> List[Dict[str, Any]]:
        """Run element-wise rate analysis on a list of BOQ items."""
        return analyze_boq_items(boq_items, zone)

    async def analyze_item(
        self,
        sor_code: str,
        description: str = "",
        quoted_rate: Optional[float] = None,
        sor_rate: Optional[float] = None,
        unit: str = "",
        quantity: float = 0,
        zone: str = "A",
    ) -> Dict[str, Any]:
        """Analyze a single BOQ item."""
        return analyze_item(sor_code, description, quoted_rate, sor_rate, unit, quantity, zone)

    async def get_profit_summary(
        self,
        boq_items: List[Dict[str, Any]],
        zone: str = "A",
    ) -> Dict[str, Any]:
        """Aggregate profit margin stats across all items that have compositions."""
        analyzed = analyze_boq_items(boq_items, zone)
        items_with_analysis = [a for a in analyzed if a.get("rate_analysis", {}).get("has_composition")]
        items_without = [a for a in analyzed if not a.get("rate_analysis", {}).get("has_composition")]

        margins = []
        total_sor = 0.0
        total_market = 0.0
        total_boq = 0.0

        for item in analyzed:
            ra = item.get("rate_analysis", {})
            if not ra.get("has_composition"):
                continue
            qty = item.get("quantity", 0) or item.get("qty", 0)
            quoted = ra.get("quoted_rate") or item.get("rate") or item.get("quoted_rate", 0)
            market_per_unit = ra.get("total_market_cost_per_unit", 0)

            if quoted and market_per_unit:
                margin = round(((quoted - market_per_unit) / market_per_unit) * 100, 2)
                margins.append(margin)
                total_boq += qty * quoted
                total_market += qty * market_per_unit

            sor = ra.get("sor_rate") or item.get("sor_rate", 0)
            if sor and market_per_unit:
                total_sor += qty * sor

        avg_margin = round(sum(margins) / len(margins), 2) if margins else None
        min_margin = min(margins) if margins else None
        max_margin = max(margins) if margins else None

        safe_items = sum(1 for m in margins if m > 15)
        tight_items = sum(1 for m in margins if 5 <= m <= 15)
        at_risk_items = sum(1 for m in margins if 0 < m < 5)
        loss_items = sum(1 for m in margins if m <= 0)

        overall_market_to_boq = round(((total_boq - total_market) / total_market) * 100, 2) if total_market else None
        overall_sor_to_boq = round(((total_boq - total_sor) / total_sor) * 100, 2) if total_sor else None

        return {
            "zone": zone,
            "items_analyzed": len(items_with_analysis),
            "items_without_composition": len(items_without),
            "avg_profit_margin_pct": avg_margin,
            "min_profit_margin_pct": min_margin,
            "max_profit_margin_pct": max_margin,
            "profit_distribution": {
                "safe_gt_15pct": safe_items,
                "tight_5_to_15pct": tight_items,
                "at_risk_0_to_5pct": at_risk_items,
                "loss_le_0pct": loss_items,
            },
            "total_boq_value": round(total_boq, 2),
            "total_market_cost": round(total_market, 2),
            "total_sor_value": round(total_sor, 2),
            "overall_markup_vs_market_pct": overall_market_to_boq,
            "overall_discount_vs_sor_pct": overall_sor_to_boq,
        }
