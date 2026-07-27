"""
Agent 18 — AI Bid Assistant
Answers the question "Should We Bid?" by analyzing resources, margin, risk, and competition.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

from app.agents.core.base import BaseAgent, AgentResult, AgentStatus
from app.agents.schemas import AIAssistantOutput

logger = logging.getLogger(__name__)


class AIBidAssistantAgent(BaseAgent):
    agent_id = "agent-018-ai-bid-assistant"
    agent_name = "AI Bid Assistant"
    description = "Provides a comprehensive bid/no-bid recommendation by analyzing resources, margin, risk, and competition. Now with LLM-powered deep analysis."
    dependencies: List[str] = [
        "agent-007-eligibility-compliance",
        "agent-008-risk-intelligence",
        "agent-011-rate-analysis",
        "agent-016-win-probability",
        "agent-019-resource-capacity",
        "agent-021-financial-intelligence",
    ]
    version = "2.0.0"

    async def execute(self, context: Dict[str, Any]) -> AgentResult:
        upstream = context.get("upstream", {})
        mode = context.get("analysis_mode", "hybrid")  # rule | llm | hybrid

        if mode == "llm" and self.llm_service:
            output = await self._analyze_with_llm(upstream, context)
        elif mode == "hybrid" and self.llm_service:
            # Rule-based first, then LLM enhancement for ambiguous cases
            rule_output = await self._analyze_rule_based(upstream, context)
            if self._is_ambiguous(rule_output):
                output = await self._enhance_with_llm(rule_output, upstream, context)
            else:
                output = rule_output
        else:
            output = await self._analyze_rule_based(upstream, context)

        return AgentResult(
            agent_id=self.agent_id,
            agent_name=self.agent_name,
            status=AgentStatus.SUCCESS,
            output=output,
        )

    async def _analyze_rule_based(self, upstream: Dict, context: Dict) -> Dict:
        """Original rule-based analysis."""
        result = AIAssistantOutput()

        resources = upstream.get("agent-019-resource-capacity", {})
        risk = upstream.get("agent-008-risk-intelligence", {})
        win_prob = upstream.get("agent-016-win-probability", {})
        financial = upstream.get("agent-021-financial-intelligence", {})

        # Resource check
        capacity = resources.get("capacity_percent", 80)
        result.resource_ok = capacity < 90

        # Margin check
        expected_margin = financial.get("margin_percent", 12)
        result.margin_ok = expected_margin >= 10

        # Risk check
        risk_level = risk.get("risk_level", "Medium")
        result.risk_ok = risk_level != "High"

        # Competition check
        win_chance = win_prob.get("win_probability", 50)
        result.competition_ok = win_chance >= 40

        # Decision
        positives = sum([result.resource_ok, result.margin_ok, result.risk_ok, result.competition_ok])
        result.should_bid = positives >= 3

        if result.should_bid:
            result.recommendation = "BID"
            result.reason = f"Positive assessment ({positives}/4 factors favorable)"
        else:
            result.recommendation = "NO-BID"
            result.reason = f"Only {positives}/4 factors favorable — insufficient confidence"

        return {
            "should_bid": result.should_bid,
            "recommendation": result.recommendation,
            "analysis": {
                "resource_ok": result.resource_ok,
                "margin_ok": result.margin_ok,
                "risk_ok": result.risk_ok,
                "competition_ok": result.competition_ok,
            },
            "reason": result.reason,
            "method": "rule_based",
        }

    def _is_ambiguous(self, output: Dict) -> bool:
        """Determine if rule-based output needs LLM enhancement."""
        # Ambiguous: 2/4 factors favorable (borderline)
        factors = output.get("analysis", {})
        positive_count = sum([
            factors.get("resource_ok", False),
            factors.get("margin_ok", False),
            factors.get("risk_ok", False),
            factors.get("competition_ok", False),
        ])
        return positive_count == 2  # Borderline case

    async def _enhance_with_llm(self, rule_output: Dict, upstream: Dict, context: Dict) -> Dict:
        """Enhance rule-based output with LLM analysis for ambiguous cases."""
        if not self.llm_service:
            return {**rule_output, "method": "rule_based"}

        try:
            llm_result = await self.llm_service.analyze_bid(
                context=upstream,
                tender=context.get("tender_info", {}),
            )
            # Merge LLM insights with rule-based output
            return {
                **rule_output,
                "llm_analysis": llm_result,
                "method": "hybrid",
                "recommendation": llm_result.get("recommendation", rule_output["recommendation"]),
                "reason": llm_result.get("reasoning", rule_output["reason"]),
                "confidence": llm_result.get("confidence", 50),
            }
        except Exception as e:
            logger.warning(f"LLM enhancement failed: {e}")
            return {**rule_output, "method": "rule_based", "llm_error": str(e)}

    async def _analyze_with_llm(self, upstream: Dict, context: Dict) -> Dict:
        """Pure LLM-based analysis."""
        if not self.llm_service:
            return await self._analyze_rule_based(upstream, context)

        try:
            result = await self.llm_service.analyze_bid(
                context=upstream,
                tender=context.get("tender_info", {}),
            )
            return {
                "should_bid": result.get("recommendation", "NO-BID") == "BID",
                "recommendation": result.get("recommendation", "NO-BID"),
                "analysis": result.get("analysis", {}),
                "reason": result.get("reasoning", "LLM analysis"),
                "confidence": result.get("confidence", 50),
                "method": "llm",
            }
        except Exception as e:
            logger.warning(f"LLM analysis failed: {e}")
            return await self._analyze_rule_based(upstream, context)
