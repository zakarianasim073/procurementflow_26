"""
Agent 10 — LERT Prediction Agent (PPR 2025 Regime-Aware)
Predicts Lowest Evaluated Responsive Tender amount using historical NPP data from the database.
Applies PPR 2008 ±10% cap or PPR 2025 SLT/ALT thresholds based on tender opening date.
"""

from __future__ import annotations

import logging
import math
from typing import Any, Dict, List, Optional

from app.agents.core.base import BaseAgent, AgentResult, AgentStatus
from app.agents.core.regime import get_regime, get_thresholds, get_slt_status, get_regime_label, REGIME_PPR2025, REGIME_PPR2008
from app.agent_schemas import LERTPrediction
from app.db.database import get_sync_engine
from sqlalchemy import text

logger = logging.getLogger(__name__)


class LERTPredictionAgent(BaseAgent):
    agent_id = "agent-010-lert-prediction"
    agent_name = "LERT Prediction Agent (Regime-Aware)"
    description = "Predicts LERT using historical NPP with PPR 2008 (±10% cap) or PPR 2025 (SLT/ALT) regime awareness."
    dependencies: List[str] = ["agent-009-ppr-evaluation", "agent-013-competitor-intelligence"]
    version = "4.0.0"

    async def execute(self, context: Dict[str, Any]) -> AgentResult:
        tender_info = context.get("tender_info", {})
        tender_value = tender_info.get("estimated_value", 0) or tender_info.get("estimated_amount_bdt", 0)
        competitors = context.get("upstream", {}).get("agent-013-competitor-intelligence", {})

        opening_date = tender_info.get("opening_date") or tender_info.get("submission_date")
        regime = get_regime(opening_date)
        thresholds = get_thresholds(regime)

        prediction = await self._predict_lert(tender_value, competitors, tender_info, regime, thresholds)

        output = {
            "tender_value": tender_value,
            "predicted_lert": prediction["predicted_lert"],
            "discount_range": prediction["discount_range"],
            "confidence_interval": prediction["confidence_interval"],
            "num_competitors_expected": prediction["num_competitors_expected"],
            "methodology": prediction["methodology"],
            "risk_assessment": prediction["risk_assessment"],
            "recommendation": prediction["recommendation"],
            "regime": regime,
            "regime_label": get_regime_label(regime),
            "slt_threshold_pct": round((1 - thresholds["slt_threshold"]) * 100, 1) if thresholds["slt_threshold"] else None,
            "alt_threshold_pct": round((1 - thresholds["alt_threshold"]) * 100, 1) if thresholds["alt_threshold"] else None,
            "cap_threshold_pct": round(thresholds["cap_threshold"] * 100, 1) if thresholds.get("cap_threshold") else None,
        }

        return AgentResult(
            agent_id=self.agent_id,
            agent_name=self.agent_name,
            status=AgentStatus.SUCCESS,
            output=output,
        )

    async def _predict_lert(
        self, tender_value: float, competitors: Dict, tender_info: Dict,
        regime: str, thresholds: Dict
    ) -> Dict:
        """Predict LERT using historical NPP data, regime-aware."""
        competitor_list = competitors.get("competitors", [])
        num_competitors_expected = len(competitor_list) if competitor_list else 0

        agency = tender_info.get("agency", tender_info.get("procuring_entity", ""))
        avg_discount, avg_npp = await self._query_historical_npp(agency, regime)

        if avg_discount > 0:
            base_discount = avg_discount
            methodology = "Historical NPP analysis from database"
        else:
            base_discount = competitors.get("market_insights", {}).get("avg_market_discount", 5.0)
            methodology = "Competitor market analysis (no historical NPP data)"

        competition_factor = 1 + (num_competitors_expected - 3) * 0.05 if num_competitors_expected > 0 else 1.0
        adjusted_discount = base_discount * competition_factor

        if regime == REGIME_PPR2025:
            slt_discount_pct = round((1 - thresholds["slt_threshold"]) * 100, 1)
            alt_discount_pct = round((1 - thresholds["alt_threshold"]) * 100, 1)
            max_allowed_discount = alt_discount_pct
            methodology += f" | PPR 2025 regime: SLT at {slt_discount_pct}% discount, ALT at {alt_discount_pct}%"
        else:
            cap_pct = round(thresholds["cap_threshold"] * 100, 1) if thresholds.get("cap_threshold") else 10.0
            max_allowed_discount = cap_pct
            methodology += f" | PPR 2008 regime: ±{cap_pct}% cap applies"

        clamped_discount = min(adjusted_discount, max_allowed_discount)

        predicted_lert = round(tender_value * (1 - clamped_discount / 100), 2) if tender_value > 0 else 0

        low_discount = max(clamped_discount * 0.7, 2.0)
        high_discount = min(clamped_discount * 1.4, max_allowed_discount)

        std_dev = clamped_discount * 0.15
        ci_lower = round(tender_value * (1 - (clamped_discount + 2 * std_dev) / 100), 2) if tender_value > 0 else 0
        ci_upper = round(tender_value * (1 - (clamped_discount - 2 * std_dev) / 100), 2) if tender_value > 0 else 0

        if clamped_discount > max_allowed_discount * 0.85:
            risk = "HIGH"
            recommendation = "Bid near ALT threshold — justification required under PPR 2025 Rule 31" if regime == REGIME_PPR2025 else "Bid near cap — possible non-responsive under PPR 2008"
        elif clamped_discount > max_allowed_discount * 0.6:
            risk = "MEDIUM"
            recommendation = "Standard competitive pricing recommended"
        else:
            risk = "LOW"
            recommendation = "Conservative pricing may be sufficient"

        return {
            "predicted_lert": predicted_lert,
            "discount_range": {
                "low": round(low_discount, 1),
                "high": round(high_discount, 1),
                "expected": round(clamped_discount, 1),
                "max_possible_under_regime": round(max_allowed_discount, 1),
            },
            "confidence_interval": {
                "lower": ci_lower,
                "upper": ci_upper,
                "confidence_level": "95%",
            },
            "num_competitors_expected": num_competitors_expected,
            "methodology": methodology,
            "risk_assessment": risk,
            "recommendation": recommendation,
        }

    async def _query_historical_npp(self, agency: str, regime: Optional[str] = None) -> tuple[float, float]:
        """Query historical NPP data from the database for this agency, optionally filtered by regime."""
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
                    SELECT AVG(av.discount_pct) as avg_discount, AVG(av.npp_ratio) as avg_npp
                    FROM award_records_v2 av
                    LEFT JOIN procurement_tenders t ON av.procurement_tender_id = t.id
                    WHERE av.agency_code = :agency AND av.discount_pct IS NOT NULL
                    {regime_filter}
                """), {"agency": agency}).fetchone()
                
                if rows and rows[0] is not None:
                    return float(rows[0] or 0), float(rows[1] or 0)
                
                rows = conn.execute(text("""
                    SELECT AVG(lowest_percent_below_oe) as avg_npp
                    FROM npp_records
                    WHERE agency = :agency
                """), {"agency": agency}).fetchone()
                
                if rows and rows[0] is not None:
                    avg_npp = float(rows[0] or 0)
                    return avg_npp, avg_npp
                    
        except Exception as e:
            logger.warning(f"Could not query historical NPP: {e}")
        
        return 0.0, 0.0
