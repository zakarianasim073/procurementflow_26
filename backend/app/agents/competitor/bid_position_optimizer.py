"""
Agent 17 — Bid Position Optimizer v3
Phase 2: Decision Intelligence Engine

Produces 3 strategic ranges: Conservative | Balanced | Aggressive
Each with expected margin, win probability, and risk assessment.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from decimal import Decimal

from app.agents.core.base import BaseAgent, AgentResult, AgentStatus
from app.agents.core.regime import get_regime, get_thresholds, get_slt_status, REGIME_PPR2025
from app.agents.core.db_helpers import lookup_estimate, get_market_intelligence
from app.db.database import get_sync_engine
from app.services.decision_calibration import decision_calibration_service
from sqlalchemy import text

logger = logging.getLogger(__name__)


class BidPositionOptimizerAgent(BaseAgent):
    agent_id = "agent-017-bid-position-optimizer"
    agent_name = "Bid Position Optimizer v3"
    description = "Regime-aware Conservative/Balanced/Aggressive bid ranges with PPR 2025 SLT threshold integration."
    dependencies = ["agent-011-rate-analysis", "agent-013-competitor-intelligence", "agent-016-win-probability"]
    version = "3.0.0"

    async def execute(self, context: Dict[str, Any]) -> AgentResult:
        tender_id = context.get("tender_id", "")
        estimate = context.get("estimate", context.get("estimated_amount", context.get("estimated_value", 0)))
        if not estimate and tender_id:
            estimate = lookup_estimate(tender_id)
        agency = context.get("agency", "")
        zone = context.get("zone", context.get("division", ""))
        company = context.get("company_profile", context.get("company", {}))
        risk_appetite = company.get("risk_appetite", "moderate")
        margin_target = company.get("margin_target", context.get("margin_target", "12"))
        regime = context.get("regime") or get_regime(context.get("opening_date") or context.get("tender_open_date"))
        thresholds = get_thresholds(regime)

        # Get market intelligence
        market = get_market_intelligence(agency, zone)
        competitor_count = market.get("avg_competitors", 5)
        avg_discount = market.get("avg_discount", 5.5)
        priors = decision_calibration_service.strategy_priors(
            agency=agency,
            zone=zone,
            estimate=float(estimate or 0),
            risk_appetite=risk_appetite,
        )

        # Generate 3 strategic ranges
        ranges = self._compute_ranges(
            estimate,
            avg_discount,
            competitor_count,
            risk_appetite,
            float(margin_target),
            priors,
            regime,
            thresholds,
        )

        # Get current win probability for each range
        for r in ranges:
            wp = decision_calibration_service.calibrated_win_probability(
                r["discount_pct"], priors, competitor_count
            )
            r["win_probability"] = wp

        result = {
            "tender_id": tender_id,
            "estimate": float(estimate),
            "market_context": {
                "avg_discount": avg_discount,
                "avg_competitors": competitor_count,
                "competition_level": "Low" if competitor_count <= 3 else "Medium" if competitor_count <= 7 else "High",
                "historical_priors": priors.get("historical_discount", {}),
                "historical_sample_size": priors.get("sample_size", 0),
                "regime": regime,
                "slt_alt_thresholds": thresholds,
                "compliance_note": "PPR 2025 has no ±10% cap; ranges are bounded by ALT/SLT risk." if regime == REGIME_PPR2025 else "PPR 2008 ±10% cap regime.",
            },
            "ranges": ranges,
            "recommendation": self._pick_optimal(ranges, risk_appetite),
            "model_version": priors.get("model_version"),
            "calibration_confidence": priors.get("confidence"),
            "feature_snapshot": priors.get("feature_snapshot", {}),
            "version": "v3.0"
        }
        decision_calibration_service.persist_artifact({
            "type": "bid_position",
            "tender_id": tender_id,
            "model_version": result["model_version"],
            "feature_snapshot": result["feature_snapshot"],
            "market_context": result["market_context"],
            "recommendation": result["recommendation"],
        })

        await self.share_knowledge(
            entry_type="bid_position", tender_id=tender_id, data=result,
            summary=f"Bid ranges: C={ranges[0]['discount_pct']}% B={ranges[1]['discount_pct']}% A={ranges[2]['discount_pct']}%",
            tags=["bid-position", "v3", regime, agency]
        )

        return AgentResult(agent_id=self.agent_id, agent_name=self.agent_name,
                          status=AgentStatus.SUCCESS, output=result)

    async def _get_market_intelligence(self, agency: str, zone: str) -> Dict:
        """Deprecated: use app.agents.core.db_helpers.get_market_intelligence directly."""
        return get_market_intelligence(agency, zone)

    def _compute_ranges(self, estimate: float, avg_discount: float, comp_count: int,
                        risk: str, margin_target: float, priors: Dict[str, Any] = None,
                        regime: str = "", thresholds: Dict[str, float] = None) -> List[Dict]:
        """
        Conservative / Balanced / Aggressive ranges.

        Balanced target uses NPPI-style weighted average:
            WA = 0.5 × avg_npp + 0.3 × zone_adjustment + 0.2 × market_avg
        Conservative = WA − 2%   Aggressive = WA + 2%
        """
        if not estimate or estimate <= 0:
            estimate = 50_000_000

        priors = priors or {}
        thresholds = thresholds or get_thresholds(regime)
        strategy_discounts = priors.get("strategy_discounts") or {}
        comp_factor = 1.0 + (comp_count - 5) * 0.03  # More competitors -> slightly higher discount
        max_discount = 60.0 if regime == REGIME_PPR2025 else thresholds.get("max_discount_pct", 10.0)

        configs = [
            ("Conservative", strategy_discounts.get("Conservative", avg_discount - 2.0) * comp_factor, margin_target * 1.3),
            ("Balanced",     strategy_discounts.get("Balanced", avg_discount) * comp_factor,        margin_target * 1.0),
            ("Aggressive",   strategy_discounts.get("Aggressive", avg_discount + 2.0) * comp_factor,  margin_target * 0.7),
        ]

        ranges = []
        for name, discount_pct, expected_margin in configs:
            discount_pct = round(max(1.0, min(max_discount, discount_pct)), 2)
            bid_amount = round(estimate * (1 - discount_pct / 100), 2)
            slt_status = get_slt_status(bid_amount, estimate, regime)
            margin = round(expected_margin - discount_pct + avg_discount * 0.5, 1)

            ranges.append({
                "strategy": name,
                "discount_pct": discount_pct,
                "bid_amount": bid_amount,
                "estimated_margin_pct": max(3, margin),
                "bid_to_estimate_pct": round((1 - discount_pct / 100) * 100, 1),
                "risk_level": "LOW" if name == "Conservative" else "MEDIUM" if name == "Balanced" else "HIGH",
                "recommended_for": self._risk_recommendation(name, risk),
                "regime": regime,
                "slt_status": slt_status,
                "evidence": {
                    "model_version": priors.get("model_version"),
                    "historical_sample_size": priors.get("sample_size", 0),
                    "calibration_confidence": priors.get("confidence", "low"),
                },
            })

        return ranges

    def _risk_recommendation(self, strategy: str, risk_appetite: str) -> str:
        mapping = {
            "Conservative": {"conservative": "Preferred", "moderate": "Alternative", "aggressive": "Last resort"},
            "Balanced": {"conservative": "Alternative", "moderate": "Preferred", "aggressive": "Alternative"},
            "Aggressive": {"conservative": "Avoid", "moderate": "Alternative", "aggressive": "Preferred"},
        }
        return mapping.get(strategy, {}).get(risk_appetite, "Alternative")

    async def _estimate_win_prob(self, discount: float, avg_discount: float, comp_count: int) -> int:
        """
        Statistical win probability estimate based on discount position and competition.

        Model: each bidder has equal theoretical probability (1/comp_count) if at market.
        Aggressive discount raises it; conservative discount lowers it.
        """
        if comp_count <= 0:
            comp_count = 5
        base_prob = 100.0 / comp_count  # e.g. 5 bidders → 20% base

        if avg_discount > 0:
            ratio = discount / avg_discount
        else:
            ratio = 1.0

        # Smooth sigmoid-like adjustment:  ratio < 1 = conservative, ratio > 1 = aggressive
        if ratio < 0.7:      # Very conservative — likely won't win
            adjustment = -15
        elif ratio < 0.9:    # Slightly below market
            adjustment = -7
        elif ratio < 1.1:    # On-market
            adjustment = 0
        elif ratio < 1.3:    # Aggressive
            adjustment = +10
        else:                # Very aggressive — wins but low margin
            adjustment = +5  # Diminishing returns above ~1.3×

        prob = round(base_prob + adjustment, 0)
        return int(max(10, min(85, prob)))

    def _pick_optimal(self, ranges: List[Dict], risk_appetite: str) -> Dict:
        """Pick the optimal range based on risk appetite."""
        preference = {"conservative": 0, "moderate": 1, "aggressive": 2}
        idx = preference.get(risk_appetite, 1)
        opt = ranges[idx] if idx < len(ranges) else ranges[1]
        return {
            "strategy": opt["strategy"],
            "discount_pct": opt["discount_pct"],
            "bid_amount": opt["bid_amount"],
            "estimated_margin_pct": opt["estimated_margin_pct"],
            "win_probability": opt.get("win_probability", 50),
            "reason": f"Based on {risk_appetite} risk profile"
        }
