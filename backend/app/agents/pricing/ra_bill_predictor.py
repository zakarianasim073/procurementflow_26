"""
Agent 29 — RA Bill & Cash Flow Predictor
Predicts RA Bill (Running Account Bill) payment delays based on historical data.
Uses DB query first, then falls back to agency norms.
"""

from __future__ import annotations

import logging
import statistics
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple
from collections import defaultdict

from app.agents.core.base import BaseAgent, AgentResult, AgentStatus
from app.db.database import get_sync_engine
from sqlalchemy import text

logger = logging.getLogger(__name__)

# Bangladesh govt RA Bill payment norms — used as fallback when no DB data
RA_BILL_NORMS = {
    "standard_days": {"avg_delay": 45, "risk": "low"},
    "PWD": {"avg_delay": 60, "risk": "medium"},
    "LGED": {"avg_delay": 75, "risk": "high"},
    "RHD": {"avg_delay": 50, "risk": "low"},
    "BWDB": {"avg_delay": 90, "risk": "critical"},
    "City_Corp": {"avg_delay": 120, "risk": "critical"},
}


class RABillPredictorAgent(BaseAgent):
    agent_id = "agent-030-ra-bill-predictor"
    agent_name = "RA Bill & Cash Flow Predictor"
    description = "Predicts Running Bill payment delays, generates cash flow schedules, and flags payment risks."
    dependencies: List[str] = []
    version = "2.0.0"

    async def execute(self, context: Dict[str, Any]) -> AgentResult:
        project_data = context.get("project_data", {})
        upstream = context.get("upstream", {}) or {}
        award_result = upstream.get("agent-014-award-intelligence", {}) or {}
        historical_awards = context.get("awards", award_result.get("awards", []))
        if not isinstance(historical_awards, list):
            historical_awards = []
        entity = project_data.get("procuring_entity", "").upper() if project_data.get("procuring_entity") else context.get("agency", "").upper() if context.get("agency") else ""
        if not entity:
            for key in ["procuring_entity", "agency", "name", "entity"]:
                val = context.get(key)
                if val and isinstance(val, str):
                    entity = val.upper()
                    break
        
        prediction = await self._predict_payment_delays(entity, historical_awards)
        ra_bills = self._generate_ra_bill_schedule(project_data, prediction)
        cash_flow = self._generate_cash_flow(ra_bills)
        
        return AgentResult(
            agent_id=self.agent_id,
            agent_name=self.agent_name,
            status=AgentStatus.SUCCESS,
            output={
                "entity_payment_profile": prediction,
                "ra_bill_schedule": ra_bills,
                "cash_flow_projection": cash_flow,
                "estimated_completion_days": project_data.get("contract_period_days", 365),
                "warnings": self._generate_warnings(prediction, cash_flow),
            },
        )

    async def _predict_payment_delays(self, entity: str, historical: List[Dict]) -> Dict[str, Any]:
        """
        Predict payment delays based on:
        1. DB query for historical payment data (primary)
        2. Historical award data (secondary)
        3. Entity-specific norms (fallback)
        """
        # Try DB query first
        db_delay = await self._query_db_payment_delays(entity)
        
        if db_delay is not None:
            predicted_delay = db_delay
            risk = self._delay_to_risk(predicted_delay)
            source = "database_historical"
        else:
            # Fallback to norms
            norm = RA_BILL_NORMS.get(entity, RA_BILL_NORMS["standard_days"])
            predicted_delay = norm["avg_delay"]
            risk = norm["risk"]
            source = "agency_norm_fallback"
        
        # Adjust based on historical data if available
        if historical:
            delays = []
            for a in historical:
                try:
                    awarded = datetime.fromisoformat(a.get("award_date", "").replace("Z", "+00:00"))
                    comp = a.get("work_completion_date", "")
                    if comp:
                        comp_date = datetime.fromisoformat(comp.replace("Z", "+00:00"))
                        delay_days = (comp_date - awarded).days - (a.get("contract_period_days", 365))
                        if delay_days > 0:
                            delays.append(delay_days)
                except (ValueError, TypeError):
                    continue
            
            if delays:
                avg_historical = statistics.mean(delays)
                predicted_delay = int((predicted_delay + avg_historical) / 2)
                source = "database_historical + award_data"
        
        # Seasonal adjustment (June = budget closing, Dec = new budget)
        now = datetime.now(timezone.utc)
        if now.month in [5, 6]:
            predicted_delay = int(predicted_delay * 1.3)
        elif now.month in [11, 12]:
            predicted_delay = int(predicted_delay * 1.15)
        
        return {
            "entity": entity,
            "predicted_avg_delay_days": predicted_delay,
            "risk_level": risk,
            "cptu_standard_days": RA_BILL_NORMS["standard_days"],
            "seasonal_adjustment_applied": now.month in [5, 6, 11, 12],
            "analysis": f"Expected ~{predicted_delay} days for RA Bill payment from {entity}",
            "data_source": source,
        }

    async def _query_db_payment_delays(self, entity: str) -> Optional[int]:
        """Query historical payment delays from eExperience/contractor data."""
        try:
            engine = get_sync_engine()
            with engine.connect() as conn:
                # Try eexperience_completed for actual payment delays
                rows = conn.execute(text("""
                    SELECT AVG(
                        EXTRACT(EPOCH FROM (completion_date - award_date)) / 86400
                        - COALESCE(contract_period_days, 365)
                    ) as avg_delay
                    FROM eexperience_completed
                    WHERE agency = :entity AND completion_date IS NOT NULL AND award_date IS NOT NULL
                """), {"entity": entity}).fetchone()
                
                if rows and rows[0] is not None:
                    delay = int(rows[0])
                    if delay > 0:
                        return delay
                        
                # Fallback to award_records lifecycle data
                rows = conn.execute(text("""
                    SELECT AVG(delay_days) FROM (
                        SELECT (completion_date - award_date) as delay_days
                        FROM procurement_lifecycle
                        WHERE agency = :entity AND completion_date IS NOT NULL
                    ) sub
                    WHERE delay_days > 0
                """), {"entity": entity}).fetchone()
                
                if rows and rows[0] is not None:
                    delay = int(rows[0])
                    if delay > 0:
                        return delay
                        
        except Exception as e:
            logger.debug(f"DB payment delay query failed: {e}")
        return None

    def _delay_to_risk(self, delay_days: int) -> str:
        """Convert delay days to risk level."""
        if delay_days <= 45:
            return "low"
        elif delay_days <= 75:
            return "medium"
        elif delay_days <= 100:
            return "high"
        else:
            return "critical"

    def _generate_ra_bill_schedule(self, project: Dict, prediction: Dict) -> List[Dict]:
        """Generate 4 hypothetical RA Bills based on 25%, 50%, 75%, 100% completion."""
        contract_value = float(project.get("estimated_cost", 0) or project.get("awarded_amount", 0))
        period_days = project.get("contract_period_days", 365)
        delay = prediction.get("predicted_avg_delay_days", 60)
        
        milestones = [25, 50, 75, 100]
        schedule = []
        
        for pct in milestones:
            milestone_value = contract_value * pct / 100
            retention = milestone_value * 0.075
            net_payable = milestone_value - retention
            
            work_day = int(period_days * pct / 100)
            submission_date = datetime.now(timezone.utc) + timedelta(days=work_day)
            expected_payment = submission_date + timedelta(days=delay)
            
            schedule.append({
                "milestone": f"{pct}%",
                "work_progress": {
                    "from_pct": max(0, pct - 25),
                    "to_pct": pct,
                },
                "milestone_value_bdt": round(milestone_value, 2),
                "retention_7.5pct": round(retention, 2),
                "net_payable_bdt": round(net_payable, 2),
                "expected_submission_date": submission_date.strftime("%Y-%m-%d"),
                "expected_payment_date": expected_payment.strftime("%Y-%m-%d"),
                "expected_delay_days": delay,
            })
        
        return schedule

    def _generate_cash_flow(self, ra_bills: List[Dict]) -> Dict[str, Any]:
        """Generate cash flow projection from RA Bill schedule."""
        total_contract = 0
        total_payable = 0
        total_retention = 0
        
        for bill in ra_bills:
            total_contract += bill["milestone_value_bdt"]
            total_payable += bill["net_payable_bdt"]
            total_retention += bill["retention_7.5pct"]
        
        return {
            "total_contract_value_bdt": round(total_contract, 2),
            "total_net_payable_bdt": round(total_payable, 2),
            "total_retention_bdt": round(total_retention, 2),
            "total_retention_pct": 7.5,
            "effective_tax_deduction": round(total_payable * 0.10, 2),
            "estimated_bank_interest_loss": round(total_payable * 0.12 * 0.1, 2),
        }

    def _generate_warnings(self, prediction: Dict, cash_flow: Dict) -> List[str]:
        """Generate actionable warnings."""
        warnings = []
        
        if prediction["risk_level"] in ("high", "critical"):
            warnings.append(
                f"⚠️ {prediction['entity']} has {prediction['risk_level']} payment risk. "
                f"Expected {prediction['predicted_avg_delay_days']} days delay. "
                f"Plan working capital accordingly."
            )
        
        if cash_flow["total_retention_bdt"] > 0:
            warnings.append(
                f"💰 ৳{cash_flow['total_retention_bdt']:,.0f} retention money will be held. "
                f"Ensure defect liability period compliance."
            )
        
        if cash_flow["estimated_bank_interest_loss"] > 0:
            warnings.append(
                f"🏦 Estimated ৳{cash_flow['estimated_bank_interest_loss']:,.0f} in bank interest "
                f"cost due to delayed payments."
            )
        
        return warnings
