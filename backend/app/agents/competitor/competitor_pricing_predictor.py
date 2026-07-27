"""
Agent 15 — Competitor Pricing Predictor (PPR 2025 Regime-Aware)
Predicts competitor bid pricing based on historical behavior, market position, and tender characteristics.
PPR 2008: ±10% cap applied to all discount predictions.
PPR 2025: SLT at 70% / ALT at 60% of estimate, no cap — predictions cap at ALT threshold.
"""

from __future__ import annotations

import logging
import math
import statistics
from typing import Any, Dict, List, Optional, Tuple

from app.agents.core.base import BaseAgent, AgentResult, AgentStatus
from app.agents.core.regime import get_regime, get_thresholds, get_regime_label, REGIME_PPR2025, REGIME_PPR2008, regime_weight
from app.db.database import get_sync_engine
from sqlalchemy import text

logger = logging.getLogger(__name__)


class CompetitorPricingPredictorAgent(BaseAgent):
    agent_id = "agent-015-competitor-pricing-predictor"
    agent_name = "Competitor Pricing Predictor (Regime-Aware)"
    description = "Predicts competitor bid prices using historical discount patterns, regime-aware (PPR 2008 ±10% cap / PPR 2025 SLT/ALT)."
    dependencies: List[str] = ["agent-013-competitor-intelligence", "agent-014-award-intelligence"]
    version = "4.0.0"

    async def execute(self, context: Dict[str, Any]) -> AgentResult:
        tender_info = context.get("tender_info", {})
        upstream = context.get("upstream", {})
        competitor_data = upstream.get("agent-013-competitor-intelligence", {})
        award_data = upstream.get("agent-014-award-intelligence", {})

        opening_date = tender_info.get("opening_date") or tender_info.get("submission_date")
        regime = get_regime(opening_date)
        thresholds = get_thresholds(regime)

        predictions = await self._predict_pricing(tender_info, competitor_data, award_data, regime, thresholds)

        return AgentResult(
            agent_id=self.agent_id,
            agent_name=self.agent_name,
            status=AgentStatus.SUCCESS,
            output=predictions,
        )

    async def _predict_pricing(self, tender: Dict, competitor_data: Dict, award_data: Dict,
                                regime: str, thresholds: Dict) -> Dict:
        """Predict pricing for each known competitor using regime-aware thresholds."""
        estimated_value = tender.get(
            "estimated_value",
            tender.get(
                "estimated_cost",
                tender.get(
                    "app_estimated_value_bdt",
                    tender.get("estimated_value_bdt", tender.get("estimated_amount_bdt", 0)),
                ),
            ),
        )
        try:
            estimated_value = float(estimated_value or 0)
        except (TypeError, ValueError):
            estimated_value = 0.0
        if estimated_value <= 0:
            return {
                "competitor_predictions": [],
                "market_prediction": {
                    "estimated_value": 0,
                    "avg_expected_bid": 0,
                    "lowest_expected_bid": 0,
                    "highest_expected_bid": 0,
                    "avg_discount_pct": 0,
                },
                "num_competitors_analyzed": 0,
                "regime": regime,
                "error": "No estimated value provided for tender",
            }

        competitors = competitor_data.get("competitors", [])
        if not competitors:
            competitors = await self._query_db_competitors(tender, regime)

        predictions = []
        for comp in competitors:
            prediction = self._predict_single_competitor(comp, estimated_value, regime, thresholds)
            predictions.append(prediction)

        if predictions:
            avg_expected = sum(p["expected_bid"] for p in predictions) / len(predictions)
            min_expected = min(p["expected_bid"] for p in predictions)
            max_expected = max(p["expected_bid"] for p in predictions)
        else:
            if regime == REGIME_PPR2025:
                slt_discount = round((1 - thresholds["slt_threshold"]) * 100, 1)
                alt_discount = round((1 - thresholds["alt_threshold"]) * 100, 1)
                avg_discount = (slt_discount + alt_discount) / 2
            else:
                cap_pct = round(thresholds["cap_threshold"] * 100, 1)
                avg_discount = cap_pct * 0.5
            avg_expected = estimated_value * (1 - avg_discount / 100)
            min_expected = estimated_value * (1 - avg_discount * 1.3 / 100)
            max_expected = estimated_value * (1 - avg_discount * 0.7 / 100)
        avg_discount_pct = round((1 - avg_expected / estimated_value) * 100, 1) if estimated_value > 0 else 0.0

        return {
            "competitor_predictions": sorted(predictions, key=lambda p: p["expected_bid"]),
            "market_prediction": {
                "estimated_value": estimated_value,
                "avg_expected_bid": round(avg_expected, 2),
                "lowest_expected_bid": round(min_expected, 2),
                "highest_expected_bid": round(max_expected, 2),
                "avg_discount_pct": avg_discount_pct,
            },
            "num_competitors_analyzed": len(predictions),
            "regime": regime,
            "regime_label": get_regime_label(regime),
            "slt_threshold_pct": round((1 - thresholds["slt_threshold"]) * 100, 1),
            "alt_threshold_pct": round((1 - thresholds["alt_threshold"]) * 100, 1),
            "cap_pct": round(thresholds["cap_threshold"] * 100, 1) if thresholds.get("cap_threshold") else None,
        }

    async def _query_db_competitors(self, tender: Dict, regime: Optional[str] = None) -> List[Dict]:
        """Query real competitors from database for this tender's agency, filtered by regime."""
        agency = tender.get("agency", tender.get("procuring_entity", ""))
        try:
            engine = get_sync_engine()
            with engine.connect() as conn:
                regime_filter = ""
                if regime == REGIME_PPR2025:
                    regime_filter = "AND t.opening_date >= '2025-09-28'"
                elif regime == REGIME_PPR2008:
                    regime_filter = "AND (t.opening_date IS NULL OR t.opening_date < '2025-09-28')"

                # sql-ok: regime filter from code constants; values bound
                rows = conn.execute(text(f"""
                    SELECT av.contractor_name, COUNT(*) as wins,
                           COALESCE(SUM(av.amount_bdt), 0) as total_value,
                           AVG(av.discount_pct) as avg_discount
                    FROM award_records_v2 av
                    LEFT JOIN procurement_tenders t ON av.procurement_tender_id = t.id
                    WHERE av.agency_code = :agency AND av.contractor_name IS NOT NULL
                    {regime_filter}
                    GROUP BY av.contractor_name
                    ORDER BY wins DESC
                    LIMIT 10
                """), {"agency": agency}).fetchall()

                competitors = []
                for row in rows:
                    if row[0] and row[0].strip():
                        w = regime_weight(regime, "pricing") if regime else 1.0
                        competitors.append({
                            "name": row[0],
                            "avg_discount": float(row[3] or 5.0) * w,
                            "win_rate": float(row[1]),
                            "total_wins": int(row[1]),
                            "preferred_agency": agency,
                            "_regime_weight": w,
                        })
                return competitors
        except Exception as e:
            logger.warning(f"Could not query DB competitors: {e}")
            return []

    def _predict_single_competitor(self, competitor: Dict, estimated_value: float,
                                    regime: str, thresholds: Dict) -> Dict:
        """Predict a single competitor's bid pricing — regime-aware discount clamping."""
        name = competitor.get("name", "Unknown")
        historical_discount: float = float(competitor.get("avg_discount") or 5.0)
        discount_stddev: float = float(competitor.get("discount_stddev") or max(0.5, historical_discount * 0.15))
        preferred_agency: str = competitor.get("preferred_agency", "")
        win_rate: float = float(competitor.get("win_rate") or 10.0)
        total_wins: int = int(competitor.get("total_wins") or 0)

        if win_rate > 15:
            discount_multiplier = 1.15
        elif win_rate > 8:
            discount_multiplier = 1.00
        else:
            discount_multiplier = 0.90

        base_discount = historical_discount * discount_multiplier

        if regime == REGIME_PPR2025:
            alt_discount_pct = round((1 - thresholds["alt_threshold"]) * 100, 1)
            slt_discount_pct = round((1 - thresholds["slt_threshold"]) * 100, 1)
            max_discount = alt_discount_pct
        else:
            cap_pct = round(thresholds["cap_threshold"] * 100, 1) if thresholds.get("cap_threshold") else 10.0
            max_discount = cap_pct

        p50_discount = round(base_discount, 2)
        p10_discount = round(max(1.0, base_discount - discount_stddev), 2)
        p90_discount = round(min(max_discount, base_discount + discount_stddev), 2)

        predicted_discount = min(p50_discount, max_discount)
        predicted_discount = max(2.0, predicted_discount)

        expected_bid = round(estimated_value * (1 - predicted_discount / 100), 2)
        low_bid = round(estimated_value * (1 - p90_discount / 100), 2)
        high_bid = round(estimated_value * (1 - p10_discount / 100), 2)

        if total_wins > 10:
            confidence = "HIGH"
        elif total_wins > 3:
            confidence = "MEDIUM"
        else:
            confidence = "LOW"

        regime_note = f"\nPPR 2025: capped at {max_discount}% (ALT threshold)" if regime == REGIME_PPR2025 else f"\nPPR 2008: capped at {max_discount}% (±10% cap)"

        return {
            "competitor_name": name,
            "historical_avg_discount": historical_discount,
            "historical_discount_stddev": discount_stddev,
            "predicted_discount": predicted_discount,
            "expected_bid": expected_bid,
            "low_bid_estimate": low_bid,
            "high_bid_estimate": high_bid,
            "discount_vs_estimate": predicted_discount,
            "confidence": confidence,
            "regime": regime,
            "max_discount_allowed": max_discount,
            "prediction_method": f"statistical_deterministic_{regime.lower()}",
            "factors": [
                f"Historical avg discount: {historical_discount}% ± {discount_stddev:.1f}%",
                f"Win-rate adjustment: ×{discount_multiplier} (win rate {win_rate:.1f}%)",
                f"Preferred agency: {preferred_agency}" if preferred_agency else "No agency preference data",
                regime_note.strip(),
            ],
        }
