"""
Agent 24 — Report Generation Agent
Generates comprehensive reports: Technical, Commercial, and Executive summaries.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

from app.agents.core.base import BaseAgent, AgentResult, AgentStatus

logger = logging.getLogger(__name__)


class ReportGenerationAgent(BaseAgent):
    agent_id = "agent-023-report-generation"
    agent_name = "Report Generation Agent"
    description = "Creates Technical, Commercial, and Executive reports with formatted output."
    dependencies: List[str] = [
        "agent-005-boq-intelligence", "agent-011-rate-analysis",
        "agent-022-executive-decision",
    ]
    version = "2.0.0"

    async def execute(self, context: Dict[str, Any]) -> AgentResult:
        tender_id = context.get("tender_id", "")
        report_types = context.get("report_types", ["technical", "commercial", "executive"])
        upstream = context.get("upstream", {})

        # Get tender info for scope description
        tender_info = context.get("tender_info", {})
        work_name = tender_info.get("work_name", tender_info.get("title", "Unknown work"))

        reports = {}
        for rtype in report_types:
            content = await self._generate_report(rtype, tender_id, upstream, context, work_name)
            reports[rtype] = content

        output = {
            "tender_id": tender_id,
            "reports_generated": len(reports),
            "reports": reports,
            "status": "Reports Generated",
        }

        return AgentResult(
            agent_id=self.agent_id,
            agent_name=self.agent_name,
            status=AgentStatus.SUCCESS,
            output=output,
        )

    async def _generate_report(self, rtype: str, tender_id: str, upstream: Dict, context: Dict, work_name: str) -> Dict:
        if rtype == "technical":
            return self._technical_report(tender_id, upstream, work_name)
        elif rtype == "commercial":
            return self._commercial_report(tender_id, upstream)
        else:
            return self._executive_report(tender_id, upstream)

    def _technical_report(self, tender_id: str, upstream: Dict, work_name: str) -> Dict:
        boq = upstream.get("agent-005-boq-intelligence", {})
        specs = upstream.get("agent-006-spec-intelligence", {})

        return {
            "title": f"Technical Report — {tender_id}",
            "sections": {
                "Scope of Work": work_name,
                "BOQ Summary": f"{boq.get('total_items', 0)} items across {len(boq.get('categories_found', []))} categories",
                "Specifications": f"{specs.get('requirements_count', 0)} technical requirements identified",
                "Risks": f"{specs.get('risks_count', 0)} special conditions flagged",
            },
        }

    def _commercial_report(self, tender_id: str, upstream: Dict) -> Dict:
        rates = upstream.get("agent-011-rate-analysis", {})
        avg_margin = rates.get("average_margin_pct")
        margin_str = f"{avg_margin:.1f}%" if avg_margin is not None else "Not calculated"
        
        return {
            "title": f"Commercial Report — {tender_id}",
            "sections": {
                "Rate Analysis": f"{rates.get('analyzed_items', 0)} items analyzed",
                "Total Value": f"Total recommended: ৳{rates.get('total_recommended_value', 0):,.2f}",
                "Margin": f"Average margin: {margin_str}",
            },
        }

    def _executive_report(self, tender_id: str, upstream: Dict) -> Dict:
        decision = upstream.get("agent-022-executive-decision", {})
        return {
            "title": f"Executive Decision Report — {tender_id}",
            "sections": {
                "Decision": decision.get("decision", "PENDING"),
                "Risk": decision.get("risk_level", "N/A"),
                "Win Chance": decision.get("win_chance_pct", "N/A"),
                "Expected Profit": decision.get("expected_profit_formatted", "N/A"),
                "Confidence": decision.get("confidence", "N/A"),
            },
        }
