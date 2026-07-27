"""
Agent 31 - Tender Preparation Agent
Orchestrates end-to-end tender preparation workflow by calling downstream agents.
"""
from app.agents.core.base import BaseAgent, AgentResult, AgentStatus
from typing import Any, Dict, List
import logging

logger = logging.getLogger(__name__)

class TenderPreparationAgent(BaseAgent):
    agent_id = "agent-031-tender-preparation"
    agent_name = "Tender Preparation"
    description = "End-to-end tender preparation orchestrator"
    dependencies = ["agent-002-tender-acquisition", "agent-032-document-preparation"]
    version = "2.0.0"

    async def execute(self, context: Dict[str, Any]) -> AgentResult:
        tender_id = context.get("tender_id", "")
        steps = context.get("steps", ["document_collection", "boq_analysis", "rate_filling", "submission"])
        failed_dependencies = context.get("failed_dependencies", [])
        completed = []
        all_passed = not failed_dependencies

        for step in steps:
            step_result = await self._run_step(step, context)
            completed.append(step_result)
            if step_result.get("status") != "completed":
                all_passed = False

        return AgentResult(status=AgentStatus.SUCCESS, output={
            "tender_id": tender_id,
            "preparation_steps": completed,
            "all_complete": all_passed,
            "degraded_mode": bool(context.get("degraded_mode") or failed_dependencies),
            "failed_dependencies": failed_dependencies,
        })

    async def _run_step(self, step: str, context: Dict) -> Dict:
        """Run a single preparation step with actual logic."""
        upstream = context.get("upstream", {})
        
        if step == "document_collection":
            acquisition = upstream.get("agent-002-tender-acquisition", {})
            docs = acquisition.get("documents", {})
            return {
                "step": step,
                "status": "completed" if docs else "incomplete",
                "documents_found": len(docs),
                "document_types": list(docs.keys()),
            }
        
        elif step == "boq_analysis":
            boq = upstream.get("agent-005-boq-intelligence", {})
            items = boq.get("items", [])
            return {
                "step": step,
                "status": "completed" if items else "incomplete",
                "items_analyzed": len(items),
            }
        
        elif step == "rate_filling":
            rates = upstream.get("agent-011-rate-analysis", {})
            analyzed = rates.get("analyzed_items", 0)
            return {
                "step": step,
                "status": "completed" if analyzed > 0 else "incomplete",
                "rates_filled": analyzed,
            }
        
        elif step == "submission":
            validation = upstream.get("agent-024-submission-validation", {})
            ready = validation.get("submission_ready", False)
            return {
                "step": step,
                "status": "completed" if ready else "incomplete",
                "validation_score": validation.get("validation_score", 0),
                "issues": validation.get("issues", []),
            }
        
        else:
            return {
                "step": step,
                "status": "unknown",
                "note": f"Unknown step: {step}",
            }
