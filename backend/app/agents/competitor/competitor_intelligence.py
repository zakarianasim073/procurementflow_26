"""
Agent 13 — Competitor Intelligence Agent
Tracks and analyzes competitor bidding behavior, win rates, discounts, and agency preferences.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from collections import defaultdict

from app.agents.core.base import BaseAgent, AgentResult, AgentStatus
from app.agents.core.regime import get_regime, get_thresholds, REGIME_PPR2025

logger = logging.getLogger(__name__)


class CompetitorIntelligenceAgent(BaseAgent):
    agent_id = "agent-013-competitor-intelligence"
    agent_name = "Competitor Intelligence Agent"
    description = "Regime-aware competitor behavior, win rates, discount patterns, SLT/ALT patterns, and agency preferences."
    dependencies: List[str] = ["agent-014-award-intelligence"]
    version = "3.0.0"

    async def execute(self, context: Dict[str, Any]) -> AgentResult:
        award_data = context.get("upstream", {}).get("agent-014-award-intelligence", {})
        awards = award_data.get("awards", context.get("awards", []))

        regime = context.get("regime") or get_regime(context.get("opening_date") or context.get("tender_open_date"))
        competitors = await self._analyze_competitors(awards, regime)
        market_insights = self._generate_market_insights(competitors, awards, regime)

        output = {
            "competitors": competitors,
            "total_competitors": len(competitors),
            "market_insights": market_insights,
            "top_competitors": sorted(competitors, key=lambda c: c["win_rate"], reverse=True)[:5],
            "regime": regime,
            "regime_breakdown": self._regime_breakdown(awards),
        }

        return AgentResult(
            agent_id=self.agent_id,
            agent_name=self.agent_name,
            status=AgentStatus.SUCCESS,
            output=output,
        )

    async def _analyze_competitors(self, awards: List[Dict], regime: str) -> List[Dict]:
        """Analyze competitor performance from award data."""
        if not awards:
            db_awards = self._query_db_awards()
            if db_awards:
                awards = db_awards
            else:
                return self._generate_default_competitors()

        # Group by winner
        winner_data = defaultdict(lambda: {
            "wins": 0, "total_value": 0.0, "discounts": [],
            "agencies": defaultdict(int), "categories": defaultdict(int),
        })

        for award in awards:
            winner = award.get("winner", "Unknown")
            data = winner_data[winner]
            data["wins"] += 1
            data["total_value"] += award.get("award_amount", 0)
            data["discounts"].append(award.get("discount_percent", 0))
            data["agencies"][award.get("procuring_entity", "Unknown")] += 1
            data["categories"][award.get("category", "Construction")] += 1
            data.setdefault("regimes", defaultdict(int))[get_regime(award.get("opening_date") or award.get("award_date"))] += 1

        competitors = []
        for name, data in winner_data.items():
            avg_discount = sum(data["discounts"]) / len(data["discounts"]) if data["discounts"] else 0
            top_agency = max(data["agencies"], key=data["agencies"].get) if data["agencies"] else "Unknown"
            slt_pattern = self._detect_slt_pattern(avg_discount, regime)
            
            competitors.append({
                "name": name,
                "win_rate": round(data["wins"] / max(len(awards), 1) * 100, 1),
                "total_wins": data["wins"],
                "total_value": round(data["total_value"], 2),
                "avg_discount": round(avg_discount, 2),
                "preferred_agency": top_agency,
                "agency_count": dict(data["agencies"]),
                "regime_breakdown": dict(data.get("regimes", {})),
                "slt_alt_pattern": slt_pattern,
            })

        return competitors

    def _query_db_awards(self) -> List[Dict]:
        """Query real awards from award_records_v2 for competitor analysis (delegated to db_helpers)."""
        from app.agents.core.db_helpers import query_awards_for_competitor_analysis
        return query_awards_for_competitor_analysis(limit=500)

    def _generate_default_competitors(self) -> List[Dict]:
        """Return empty — no mock data. Pipeline should provide upstream awards."""
        return []

    def _generate_market_insights(self, competitors: List[Dict], awards: List[Dict], regime: str) -> Dict:
        """Generate market-level insights from competitor analysis."""
        if not competitors:
            return {"avg_competitors_per_tender": 0, "avg_market_discount": 0}
        
        avg_win_rate = sum(c["win_rate"] for c in competitors) / len(competitors)
        avg_discount = sum(c["avg_discount"] for c in competitors) / len(competitors)
        
        return {
            "avg_competitors_per_tender": round(len(awards) / max(len(competitors), 1), 1) if awards else 5.0,
            "avg_market_discount": round(avg_discount, 2),
            "avg_win_rate": round(avg_win_rate, 1),
            "market_concentration": "High" if len(competitors) <= 3 else "Medium" if len(competitors) <= 7 else "Low",
            "total_market_value": round(sum(c["total_value"] for c in competitors), 2),
            "regime": regime,
            "slt_alt_patterns": sum(1 for c in competitors if c.get("slt_alt_pattern", {}).get("risk") != "normal"),
        }

    def _detect_slt_pattern(self, avg_discount: float, regime: str) -> Dict[str, Any]:
        if regime != REGIME_PPR2025:
            return {"risk": "legacy_cap", "note": "PPR 2008 discount cap regime"}
        thresholds = get_thresholds(regime)
        slt_discount = round((1 - thresholds.get("slt_threshold", 0.70)) * 100, 2)
        alt_discount = round((1 - thresholds.get("alt_threshold", 0.60)) * 100, 2)
        if avg_discount >= alt_discount - 1:
            return {"risk": "alt_edge", "note": "Average discount is near ALT threshold"}
        if avg_discount >= slt_discount - 1:
            return {"risk": "slt_edge", "note": "Average discount is near SLT threshold"}
        return {"risk": "normal", "note": "No SLT/ALT edge pattern detected"}

    def _regime_breakdown(self, awards: List[Dict]) -> Dict[str, int]:
        counts: Dict[str, int] = defaultdict(int)
        for award in awards:
            counts[get_regime(award.get("opening_date") or award.get("award_date"))] += 1
        return dict(counts)
