"""
Agent 22 - Executive Decision Agent
Makes bid/no-bid recommendations with confidence scoring.
"""
from app.agents.core.base import BaseAgent, AgentResult, AgentStatus
from typing import Any, Dict
import logging
from app.services.decision_calibration import decision_calibration_service

logger = logging.getLogger(__name__)

class ExecutiveDecisionAgent(BaseAgent):
    agent_id = "agent-022-executive-decision"
    agent_name = "Executive Decision"
    description = "Bid/no-bid recommendation engine"
    dependencies = ["agent-016-win-probability", "agent-017-bid-position-optimizer"]
    version = "1.0.0"

    async def execute(self, context: Dict[str, Any]) -> AgentResult:
        degraded_mode = bool(context.get("degraded_mode", False))
        failed_deps = context.get("failed_dependencies", [])
        tender_id = context.get("tender_id", "")
        
        win_prob = float(context.get("win_probability", 0) or 0)
        margin = float(context.get("expected_margin", 0) or 0)
        capacity = bool(context.get("capacity_available", True))
        
        # Gather intelligence from other agents before making decision
        gathered = {}
        if self.brain and tender_id:
            # Ask Win Probability for fresh prediction
            try:
                wp = await self.ask_agent(
                    "agent-016-win-probability",
                    "predict_win_probability",
                    {"tender_id": tender_id, "context": context}
                )
                if wp:
                    gathered["win_probability_result"] = wp
            except Exception as exc:
                logger.warning("Win Probability agent unavailable: %s", exc)
            
            # Ask Bid Position Optimizer for discount range
            try:
                bpo = await self.ask_agent(
                    "agent-017-bid-position-optimizer",
                    "optimize_bid_position",
                    {"tender_id": tender_id, "context": context}
                )
                if bpo:
                    gathered["bid_position_result"] = bpo
            except Exception as exc:
                logger.warning("Bid Position Optimizer unavailable: %s", exc)
            
            # Ask Resource Capacity for workload check
            try:
                rc = await self.ask_agent(
                    "agent-019-resource-capacity",
                    "check_capacity",
                    {"tender_id": tender_id}
                )
                if rc:
                    gathered["capacity_result"] = rc
            except Exception as exc:
                logger.warning("Resource Capacity agent unavailable: %s", exc)

        win_source = gathered.get("win_probability_result") or {}
        bid_source = gathered.get("bid_position_result") or {}
        capacity_source = gathered.get("capacity_result") or {}

        if isinstance(win_source, dict):
            win_prob = float(
                win_source.get("probability", win_source.get("win_probability", win_prob)) or win_prob
            )
        if isinstance(bid_source, dict):
            recommendation = bid_source.get("recommendation", {}) or {}
            ranges = bid_source.get("ranges", []) or []
            fallback_range = ranges[1] if len(ranges) > 1 and isinstance(ranges[1], dict) else {}
            margin = float(
                recommendation.get("estimated_margin_pct")
                if isinstance(recommendation, dict) and recommendation.get("estimated_margin_pct") is not None
                else fallback_range.get("estimated_margin_pct", margin)
            )
        if isinstance(capacity_source, dict):
            capacity = bool(capacity_source.get("has_capacity", capacity))
        
        evidence_score = 0.35
        if gathered:
            evidence_score += min(0.45, len(gathered) * 0.15)
        if not degraded_mode:
            evidence_score += 0.10
        if capacity:
            evidence_score += 0.10
        policy = decision_calibration_service.executive_policy({
            "tender_id": tender_id,
            "win_probability": win_prob,
            "expected_margin": margin,
            "capacity_available": capacity,
            "degraded_mode": degraded_mode,
            "failed_dependency_count": len(failed_deps),
            "evidence_score": round(min(1.0, evidence_score), 3),
            "intel_source_count": len(gathered),
        })
        score = policy["score"]
        decision = policy["decision"]
        confidence_level = policy["confidence_level"]
        decision_calibration_service.persist_artifact({
            "type": "executive_decision",
            "tender_id": tender_id,
            **policy,
        })
        
        # Share decision to knowledge lake when the Brain is attached; keep the
        # decision usable in standalone/test runs.
        if self.brain:
            try:
                await self.share_knowledge(
                    entry_type="executive_decision",
                    tender_id=tender_id,
                    data={
                        "decision": decision,
                        "score": score,
                        "threshold": policy.get("threshold"),
                        "model_version": policy.get("model_version"),
                        "confidence_level": confidence_level,
                        "degraded_mode": degraded_mode,
                        "failed_dependencies": failed_deps,
                        "intel_gathered": gathered,
                    },
                    summary=f"Decision: {decision} (confidence: {confidence_level}, score: {score:.1f})",
                    tags=["executive_decision", decision.lower()]
                )
            except Exception as exc:
                logger.warning("Executive decision knowledge share failed: %s", exc)
        
        return AgentResult(status=AgentStatus.SUCCESS, output={
            "decision": decision,
            "confidence_score": round(score, 1),
            "decision_threshold": policy.get("threshold"),
            "confidence_level": confidence_level,
            "model_version": policy.get("model_version"),
            "degraded_mode": degraded_mode,
            "failed_dependencies": failed_deps,
            "factors": {"win_probability": win_prob, "expected_margin": margin, "capacity": capacity},
            "feature_snapshot": policy.get("feature_snapshot", {}),
            "explanation": policy.get("explanation", {}),
            "intel_sources": gathered,
        })
