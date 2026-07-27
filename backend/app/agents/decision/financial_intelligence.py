"""
Agent 21 — Financial Intelligence Agent v2
Analyzes financial capacity, cash flow, bid bonding capacity, and working capital
using actual contractor history from PostgreSQL (award_records_v2, contractor_dna, eexperience).
No hardcoded defaults — all numbers derived from real data.
"""
from __future__ import annotations
import logging
from typing import Any, Dict, Optional
from sqlalchemy import text

from app.agents.core.base import BaseAgent, AgentResult, AgentStatus
from app.db.database import get_sync_engine

logger = logging.getLogger(__name__)


class FinancialIntelligenceAgent(BaseAgent):
    agent_id = "agent-021-financial-intelligence"
    agent_name = "Financial Intelligence"
    description = "Analyzes financial capacity using actual contractor history from PostgreSQL."
    dependencies = ["agent-007-eligibility-compliance"]
    version = "2.0.0"

    async def execute(self, context: Dict[str, Any]) -> AgentResult:
        contractor_name = context.get("contractor_name", context.get("company_name", ""))
        estimate = float(context.get("estimated_amount", context.get("estimate", 0)) or 0)
        turnover_override = float(context.get("turnover", 0) or 0)
        liquid_assets = float(context.get("liquid_assets", 0) or 0)

        # ── Query real data ──────────────────────────────────────────
        engine = get_sync_engine()
        awards_total = 0.0
        avg_award = 0.0
        award_count = 0
        dna_health = 0.0
        running_contracts = 0
        running_total = 0.0

        with engine.connect() as conn:
            if contractor_name:
                # Award history
                award_rows = conn.execute(text("""
                    SELECT COUNT(*) AS cnt, COALESCE(SUM(amount_bdt), 0) AS total,
                           COALESCE(AVG(amount_bdt), 0) AS avg_amt
                    FROM award_records_v2
                    WHERE contractor_name ILIKE :name
                      AND amount_bdt > 0
                """), {"name": f"%{contractor_name}%"}).fetchone()
                if award_rows:
                    award_count = int(award_rows.cnt or 0)
                    awards_total = float(award_rows.total or 0)
                    avg_award = float(award_rows.avg_amt or 0)

                # Contractor DNA health score
                dna_row = conn.execute(text("""
                    SELECT cd.health_score, cd.win_rate, cd.total_contracts, cd.total_amount_bdt
                    FROM contractor_dna cd
                    JOIN contractors c ON c.id = cd.contractor_id
                    WHERE c.contractor_name ILIKE :name
                    LIMIT 1
                """), {"name": f"%{contractor_name}%"}).fetchone()
                if dna_row:
                    dna_health = float(dna_row.health_score or 0)
                    if not award_count:
                        award_count = int(dna_row.total_contracts or 0)
                    if awards_total <= 0:
                        awards_total = float(dna_row.total_amount_bdt or 0)

                # Running/ongoing contracts from eExperience
                ongoing = conn.execute(text("""
                    SELECT COUNT(*) AS cnt, COALESCE(SUM(contract_value_bdt), 0) AS total
                    FROM eexperience_completed
                    WHERE contractor_name ILIKE :name
                      AND work_status = 'Ongoing'
                """), {"name": f"%{contractor_name}%"}).fetchone()
                if ongoing:
                    running_contracts = int(ongoing.cnt or 0)
                    running_total = float(ongoing.total or 0)

        # ── Compute financial metrics ────────────────────────────────
        annual_turnover = max(turnover_override, awards_total / max(award_count / 3, 1) if award_count > 0 else 0)
        working_capital = annual_turnover * 0.25 + liquid_assets * 0.5
        bonding_capacity = annual_turnover * 0.20  # PPR 2025: max 20% of turnover
        bid_security_needed = estimate * 0.01  # 1% of estimate

        # Tender absorption:  A × N × 2 − B  (PPR formula)
        max_tender_capacity = annual_turnover * award_count * 2 - running_total if award_count > 0 else 0

        sufficient_capacity = working_capital >= estimate * 0.10
        sufficient_bonding = bonding_capacity >= bid_security_needed
        has_absorption = max_tender_capacity > estimate if running_contracts > 0 else True

        # ── Risk scoring (0-100) ─────────────────────────────────────
        cashflow_score = min(100.0, (working_capital / max(estimate * 0.10, 1)) * 50)
        bonding_score = 100.0 if sufficient_bonding else (bonding_capacity / max(bid_security_needed, 1)) * 50
        absorption_score = 100.0 if has_absorption else max(20.0, (max_tender_capacity / max(estimate, 1)) * 50)

        overall_risk = round((cashflow_score * 0.35) + (bonding_score * 0.25) + (absorption_score * 0.25) + (dna_health * 15), 1)

        return AgentResult(status=AgentStatus.SUCCESS, output={
            "financial_capacity_bdt": round(working_capital, 2),
            "annual_turnover_estimated": round(annual_turnover, 2),
            "max_bonding_capacity_bdt": round(bonding_capacity, 2),
            "bid_security_required": round(bid_security_needed, 2),
            "sufficient_for_bid": sufficient_capacity and sufficient_bonding,
            "recommendation": "proceed" if overall_risk >= 60 else "caution" if overall_risk >= 40 else "high_risk",
            "risk_score": overall_risk,
            "breakdown": {
                "cashflow_score": round(cashflow_score, 1),
                "bonding_score": round(bonding_score, 1),
                "absorption_score": round(absorption_score, 1),
                "dna_health_contribution": round(dna_health * 15, 1),
            },
            "data_sources": {
                "awards_analyzed": award_count,
                "total_awards_bdt": round(awards_total, 2),
                "avg_award_bdt": round(avg_award, 2),
                "running_contracts": running_contracts,
                "running_contracts_value_bdt": round(running_total, 2),
                "dna_health_score": round(dna_health, 2),
                "max_tender_absorption_bdt": round(max(max_tender_capacity, 0), 2),
            },
            "version": "2.0",
        })