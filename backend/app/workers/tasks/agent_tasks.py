"""
Procurement Flow Specialist BD — Agent Pipeline Celery Tasks
Background wrappers for the 27-agent system.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional
from pathlib import Path

from app.celery_app import celery_app
from app.agents import AgentRegistry
from sqlalchemy import text

logger = logging.getLogger("procureflow.tasks")


def _update_agent_job(job_id: str | None, *, state: str, result_id: str | None = None, error: str | None = None) -> None:
    if not job_id:
        return
    try:
        from app.db.database import session_scope

        with session_scope() as session:
            session.execute(text("""
                UPDATE agent_jobs
                SET state = :state,
                    attempts = attempts + CASE WHEN :state = 'processing' THEN 1 ELSE 0 END,
                    result_id = COALESCE(:result_id, result_id),
                    last_error = :error,
                    updated_at = now()
                WHERE id = :job_id
            """), {
                "job_id": job_id,
                "state": state,
                "result_id": result_id,
                "error": error,
            })
    except Exception as exc:
        logger.warning("Could not update agent job %s to %s: %s", job_id, state, exc)


def get_registry() -> AgentRegistry:
    """Get or initialize the agent registry."""
    registry = AgentRegistry()
    # Register agents if not already done
    if registry.count == 0:
        from app.agents import (
            TenderRadarAgent, TenderAcquisitionAgent, CorrigendumWatchdogAgent,
            DocumentAIAgent, BOQIntelligenceAgent, SpecIntelligenceAgent,
            EligibilityComplianceAgent, RiskIntelligenceAgent, PPREvaluationAgent,
            LERTPredictionAgent, RateAnalysisAgent, MarketRateIntelligenceAgent,
            CompetitorIntelligenceAgent, AwardIntelligenceAgent, CompetitorPricingPredictorAgent,
            WinProbabilityAgent, BidPositionOptimizerAgent, AIBidAssistantAgent,
            ResourceCapacityAgent, FinancialIntelligenceAgent, ExecutiveDecisionAgent,
            EGPRateFillAgent, SubmissionValidationAgent, ReportGenerationAgent,
            KnowledgeLakeAgent, LearningAgent, WorkflowOrchestrator,
        )
        agents = [
            TenderRadarAgent(), TenderAcquisitionAgent(), CorrigendumWatchdogAgent(),
            DocumentAIAgent(), BOQIntelligenceAgent(), SpecIntelligenceAgent(),
            EligibilityComplianceAgent(), RiskIntelligenceAgent(), PPREvaluationAgent(),
            LERTPredictionAgent(), RateAnalysisAgent(), MarketRateIntelligenceAgent(),
            CompetitorIntelligenceAgent(), AwardIntelligenceAgent(), CompetitorPricingPredictorAgent(),
            WinProbabilityAgent(), BidPositionOptimizerAgent(), AIBidAssistantAgent(),
            ResourceCapacityAgent(), FinancialIntelligenceAgent(), ExecutiveDecisionAgent(),
            EGPRateFillAgent(), SubmissionValidationAgent(), ReportGenerationAgent(),
            KnowledgeLakeAgent(), LearningAgent(), WorkflowOrchestrator(),
        ]
        registry.register_many(*agents)
        logger.info(f"Registered {registry.count} agents in Celery worker")
    return registry


@celery_app.task(bind=True, max_retries=3, name="run_agent_task")
def run_agent_task(self, agent_id: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Run a single agent in the background.
    Returns the AgentResult as a dict.
    """
    import asyncio
    
    if context is None:
        context = {}
    job_id = context.pop("_agent_job_id", None)
    
    try:
        _update_agent_job(job_id, state="processing")
        registry = get_registry()
        agent = registry.get(agent_id)
        if not agent:
            error = f"Agent {agent_id} not found"
            _update_agent_job(job_id, state="failed", error=error)
            return {"error": error, "status": "failed"}
        
        # Run async agent in sync context
        result = asyncio.run(agent.run(context))
        payload = result.to_dict()
        _update_agent_job(job_id, state="done", result_id=payload.get("id") or payload.get("run_id"))
        return payload
        
    except Exception as exc:
        logger.error(f"Agent task {agent_id} failed: {exc}")
        _update_agent_job(job_id, state="failed", error=str(exc))
        self.retry(exc=exc, countdown=10)


@celery_app.task(bind=True, max_retries=2, name="run_pipeline_task")
def run_pipeline_task(self, mode: str = "full", phase: Optional[str] = None,
                      agent_ids: Optional[List[str]] = None,
                      context: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Run the full pipeline or a specific phase in the background.
    Returns aggregated results from all executed agents.
    """
    import asyncio
    
    if context is None:
        context = {}
    job_id = context.pop("_agent_job_id", None)
    
    try:
        _update_agent_job(job_id, state="processing")
        registry = get_registry()
        orch = registry.get("agent-027-orchestrator")
        if not orch:
            error = "Orchestrator not available"
            _update_agent_job(job_id, state="failed", error=error)
            return {"error": error, "status": "failed"}
        
        ctx = dict(context)
        ctx["mode"] = mode
        if phase:
            ctx["phase"] = phase
        if agent_ids:
            ctx["agent_ids"] = agent_ids
        
        try:
            result = asyncio.run(orch.run(ctx))
            payload = result.to_dict()
            _update_agent_job(job_id, state="done", result_id=payload.get("id") or payload.get("run_id"))
            return payload
        except Exception as e:
            _update_agent_job(job_id, state="failed", error=str(e))
            return {"error": str(e), "status": "failed"}
            
    except Exception as exc:
        logger.error(f"Pipeline task failed: {exc}")
        _update_agent_job(job_id, state="failed", error=str(exc))
        self.retry(exc=exc, countdown=10)


@celery_app.task(bind=True, max_retries=2, name="enforce_data_retention")
def enforce_data_retention(self) -> Dict[str, Any]:
    """
    Enforce all registered data retention policies.
    Deletes old rows from agent_results, knowledge_entries, webhook logs, etc.
    """
    import asyncio

    from app.core.data_retention import retention_manager
    from app.db.database import get_async_session

    # Register default policies if not already done
    retention_manager.register_default_policies()

    async def _run():
        async with get_async_session() as session:
            results = await retention_manager.enforce_all(session)
            return results

    try:
        results = asyncio.run(_run())
        total = sum(v for v in results.values() if v > 0)
        logger.info(f"Data retention completed: {total} rows deleted across {len(results)} tables")
        return {"status": "success", "deleted": results, "total_deleted": total}
    except Exception as exc:
        logger.error(f"Data retention task failed: {exc}")
        self.retry(exc=exc, countdown=60)


@celery_app.task(bind=True, max_retries=3, name="process_tender_bundle_task")
def process_tender_bundle_task(self, tender_id: str, file_paths: Dict[str, str],
                              sor_agency: str = "BWDB", zone: Optional[str] = None) -> Dict[str, Any]:
    """
    Process a full tender bundle in the background.
    """
    import asyncio
    
    try:
        from app.services.tender_bundle import tender_bundle_processor
        
        result = asyncio.run(
            tender_bundle_processor.process_from_paths(
                tender_id=tender_id,
                file_paths=file_paths,
                sor_agency=sor_agency,
                zone=zone,
            )
        )
        return result
        
    except Exception as exc:
        logger.error(f"Bundle task {tender_id} failed: {exc}")
        self.retry(exc=exc, countdown=10)
