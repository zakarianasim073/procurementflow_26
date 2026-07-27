"""
Agent System, Pipeline, and Orchestration API Router.
Contains all /api/agents/*, /api/pipeline/*, /api/system/*, /api/agent-results/*,
/api/tender-radar, /api/repo/facts, and /api/agents/egp/*, /api/agents/ollama-run endpoints.
"""

import asyncio
import json
import logging
import os
import sys
import uuid
from pathlib import Path
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents import AgentRegistry
from app.api.brain_router import get_brain
from app.api.v1.helpers import clamp_limit, redis_broker_available, load_tender_snapshot
from app.core.security import get_current_user, get_optional_user
from app.db.base import get_async_session

logger = logging.getLogger("procureflow")
router = APIRouter()


async def _run_egp_subprocess(payload: Dict[str, Any]) -> Dict[str, Any]:
    script = Path(__file__).resolve().parents[2] / "agents" / "discovery" / "_egp_api_probe.py"
    process = await asyncio.create_subprocess_exec(
        sys.executable,
        str(script),
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await asyncio.wait_for(
        process.communicate(json.dumps(payload).encode("utf-8")),
        timeout=60,
    )
    if process.returncode != 0:
        logger.error("e-GP subprocess failed: %s", stderr.decode("utf-8", errors="replace")[-500:])
        raise HTTPException(status_code=502, detail="e-GP operation failed")
    try:
        return json.loads(stdout.decode("utf-8"))
    except json.JSONDecodeError:
        raise HTTPException(status_code=502, detail="Invalid e-GP subprocess response")


async def _tenant_exists(db: AsyncSession, tenant_id: str | None) -> bool:
    if not tenant_id:
        return False
    row = await db.execute(text("SELECT 1 FROM tenants WHERE id = :tenant_id"), {"tenant_id": tenant_id})
    return row.scalar_one_or_none() is not None


async def _persist_agent_job(
    db: AsyncSession,
    *,
    job_id: str,
    request_id: str,
    agent_id: str,
    context: Dict[str, Any],
    user: Dict[str, Any],
    priority: int = 0,
) -> None:
    tenant_id = user.get("tenant_id") if await _tenant_exists(db, user.get("tenant_id")) else None
    await db.execute(text("""
        INSERT INTO agent_jobs (
            id, tenant_id, agent_id, request_id, tender_id, state,
            priority, attempts, max_attempts, input_data, created_at, updated_at
        )
        VALUES (
            :id, :tenant_id, :agent_id, :request_id, :tender_id, 'pending',
            :priority, 0, 3, :input_data, now(), now()
        )
    """), {
        "id": job_id,
        "tenant_id": tenant_id,
        "agent_id": agent_id,
        "request_id": request_id,
        "tender_id": str(context.get("tender_id") or ""),
        "priority": priority,
        "input_data": json.dumps(context, default=str),
    })
    await db.commit()


# ── Request/Response Models ───────────────────────────────────────────────

class WhatsAppAgentRunRequest(BaseModel):
    action: str = "send_summary"
    phone: str = ""
    message: str = ""
    tender_id: str = ""
    language: str = "bn"
    tenders: List[Dict[str, Any]] = []


class BrowserBridgeArtifact(BaseModel):
    name: str = ""
    url: str = ""
    type: str = ""
    mime_type: str = ""
    base64: str = ""
    text: str = ""


class TenderBrowserBridgeRequest(BaseModel):
    tender_id: str
    browser_capture: Dict[str, Any] = {}
    artifacts: List[BrowserBridgeArtifact] = []


# ── Agent Endpoints ───────────────────────────────────────────────────────

@router.get("/agents/registered")
async def list_registered_agents(user: Dict[str, Any] = Depends(get_current_user)):
    """List all registered agents (alias for /api/agents)."""
    registry = AgentRegistry()
    agents = []
    for agent_id in sorted(registry._agents.keys()):
        agent = registry.get(agent_id)
        if agent:
            info = agent.info()
            agents.append({
                "id": agent_id,
                "name": info.get("name", agent_id),
                "type": info.get("type", "unknown"),
                "description": info.get("description", ""),
            })
    return {"agents": agents, "total": len(agents)}


@router.get("/agents/brain-status")
async def brain_status_alias(user: Dict[str, Any] = Depends(get_current_user)):
    """Brain status (alias for /api/brain/status)."""
    from app.api.brain_router import get_brain
    brain = get_brain()
    stats = brain.get_stats()
    return {
        "agents_registered": stats.get("registered_agents", 0),
        "queue_size": stats.get("queue_size", 0),
        "knowledge_entries": stats.get("knowledge_entries", 0),
        "agents": stats.get("agents", []),
        "message_handlers": stats.get("active_handlers", 0),
    }


@router.get("/agents/recent-runs")
async def recent_runs_alias(
    limit: int = Query(12, ge=1, le=50),
    db: AsyncSession = Depends(get_async_session),
    user: Dict[str, Any] = Depends(get_current_user),
):
    """Recent runs (alias for /api/agent-results/recent)."""
    from sqlalchemy import select
    from app.db import AgentResult as AgentResultModel
    rows = (
        await db.execute(
            select(AgentResultModel)
            .order_by(AgentResultModel.created_at.desc())
            .limit(clamp_limit(limit, default=12, maximum=50))
        )
    ).scalars().all()
    return {
        "total": len(rows),
        "results": [
            {
                "run_id": str(r.id),
                "source": "database",
                "timestamp": r.created_at.isoformat() if r.created_at else "",
                "tender_id": r.tender_id or "",
                "agent_id": r.agent_id,
                "agent_name": r.agent_name or r.agent_id,
                "status": r.status,
                "output": r.output or {},
                "error": r.error or "",
                "execution_time_ms": r.execution_time_ms or 0,
            }
            for r in rows
        ],
    }


@router.get("/agents/pipeline-phases")
async def pipeline_phases_alias(user: Dict[str, Any] = Depends(get_current_user)):
    """Pipeline phases (alias for /api/pipeline/phases)."""
    from app.agents.orchestrator import PIPELINE_DEFINITION, PipelinePhase
    return {
        "phases": {
            p.value: {
                "agents": PIPELINE_DEFINITION[p],
                "count": len(PIPELINE_DEFINITION[p]),
            }
            for p in PipelinePhase
        }
    }


@router.get("/agents/{agent_id}")
async def get_agent(agent_id: str, user: Dict[str, Any] = Depends(get_current_user)):
    """Get detailed info about a specific agent."""
    registry = AgentRegistry()
    agent = registry.get(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")
    return agent.info()


@router.get("/agent-results/recent")
async def recent_agent_results(limit: int = Query(12, ge=1, le=50), db=Depends(get_async_session)):
    """Return the most recent persisted agent runs for the UI."""
    from sqlalchemy import select
    from app.db import AgentResult as AgentResultModel

    rows = (
        await db.execute(
            select(AgentResultModel)
            # Watchdog/circuit-breaker tests deliberately persist failure and
            # recovery probes. Keep that history in PostgreSQL, but do not
            # publish it as production opportunity intelligence.
            .where(~AgentResultModel.agent_id.ilike("test-%"))
            .order_by(AgentResultModel.created_at.desc())
            .limit(clamp_limit(limit, default=12, maximum=50))
        )
    ).scalars().all()

    return {
        "total": len(rows),
        "results": [
            {
                "run_id": row.id,
                "source": "database",
                "timestamp": row.created_at.isoformat() if row.created_at else "",
                "tender_id": row.tender_id or "",
                "agent_id": row.agent_id,
                "agent_name": row.agent_name or row.agent_id,
                "status": row.status,
                "output": row.output or {},
                "error": row.error or "",
                "execution_time_ms": row.execution_time_ms or 0,
            }
            for row in rows
        ],
    }


@router.post("/agents/whatsapp-automation/run")
async def run_whatsapp_agent(req: WhatsAppAgentRunRequest, user: dict = Depends(get_current_user)):
    """Run WhatsApp Automation Agent (agent-031-whatsapp-automation)."""
    from app.agents.whatsapp_agent import WhatsAppAutomationAgent
    agent = WhatsAppAutomationAgent()
    context = {
        "action": req.action,
        "phone": req.phone,
        "message": req.message,
        "tender_id": req.tender_id,
        "language": req.language,
        "tenders": req.tenders,
    }
    result = await agent.run(context)
    return {"success": result.status.value == "success", "result": result.to_dict()}


@router.post("/agents/{agent_id}/run")
async def run_agent(agent_id: str, context: Dict[str, Any] = {}, user: dict = Depends(get_current_user)):
    """Execute a specific agent with context."""
    if agent_id == "agent-002-tender-acquisition" and not str(context.get("tender_id", "")).strip():
        raise HTTPException(
            status_code=400,
            detail="Tender Acquisition requires a tender_id. Enter a Tender ID before running this agent.",
        )
    if agent_id == "agent-002-tender-acquisition":
        context = dict(context)
        context.setdefault("agent_timeout_seconds", 180)
        context.setdefault("acquisition_subprocess_timeout_seconds", 60)
    registry = AgentRegistry(get_brain())
    result = await registry.run_agent(agent_id, context)
    if result.status.value == "failed":
        raise HTTPException(status_code=500, detail=result.to_dict())
    return result.to_dict()


@router.post("/agents/tender-acquisition/browser-bridge")
async def import_tender_acquisition_browser_bridge(req: TenderBrowserBridgeRequest, user: dict = Depends(get_current_user)):
    """Persist browser-captured authenticated tender artifacts into runtime storage."""
    from app.agents.discovery.tender_acquisition import TenderAcquisitionAgent

    agent = TenderAcquisitionAgent()
    result = agent.import_browser_bridge_artifacts(
        {
            "tender_id": req.tender_id,
            "browser_capture": req.browser_capture,
            "artifacts": [artifact.model_dump() for artifact in req.artifacts],
        }
    )
    return {"success": True, **result}


@router.post("/agents/{agent_id}/run-async")
async def run_agent_async(
    agent_id: str,
    context: Dict[str, Any] = {},
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    """Run a single agent in the background via Celery."""
    from app.workers.tasks import run_agent_task

    if not redis_broker_available():
        raise HTTPException(status_code=503, detail="Redis/Celery broker is unavailable")

    job_id = str(uuid.uuid4())
    queued_context = dict(context or {})
    queued_context["_agent_job_id"] = job_id
    task = run_agent_task.delay(agent_id=agent_id, context=queued_context)
    try:
        await _persist_agent_job(
            db,
            job_id=job_id,
            request_id=task.id,
            agent_id=agent_id,
            context=context or {},
            user=user,
            priority=int((context or {}).get("priority") or 0),
        )
    except Exception:
        await db.rollback()
        logger.exception("Failed to persist agent job %s for task %s", job_id, task.id)

    return {
        "success": True,
        "job_id": job_id,
        "task_id": task.id,
        "status_url": f"/api/pipeline/status/{task.id}",
        "message": f"Agent {agent_id} started in background",
    }


# ── eGP Endpoints ─────────────────────────────────────────────────────────

@router.post("/agents/egp/login")
async def egp_login(credentials: Dict[str, str] = {}, user: dict = Depends(get_current_user)):
    """Test eGP portal login credentials."""
    email = credentials.get("email", os.getenv("EGP_EMAIL", ""))
    password = credentials.get("password", os.getenv("EGP_PASSWORD", ""))

    if not email or not password:
        raise HTTPException(status_code=400, detail="eGP credentials required")

    result = await _run_egp_subprocess({
        "action": "login",
        "email": email,
        "password": password,
    })
    success = bool(result.get("success"))
    return {
        "success": success,
        "message": "Login successful" if success else "Login failed",
        "session_active": bool(result.get("session_active")) if success else False,
    }


@router.post("/agents/egp/search")
async def egp_search(query: Dict[str, Any] = {}, user: dict = Depends(get_current_user)):
    """Search tenders on eGP portal."""
    email = os.getenv("EGP_EMAIL", "")
    password = os.getenv("EGP_PASSWORD", "")
    tender_id = query.get("tender_id", "")

    if not email or not password:
        raise HTTPException(status_code=400, detail="eGP credentials not configured")

    result = await _run_egp_subprocess({
        "action": "search",
        "email": email,
        "password": password,
        "tender_id": tender_id,
    })
    if not result.get("authenticated"):
        raise HTTPException(status_code=401, detail="eGP login failed")
    return {"success": True, "results": result.get("results", [])}


# ── Ollama Agent Runner ───────────────────────────────────────────────────

from app.core.ollama_client import OllamaClient

ollama_client = OllamaClient()


@router.post("/agents/ollama-run")
async def ollama_agent_run(request: Dict[str, Any], user: dict = Depends(get_current_user)):
    """Run agents via natural language using Ollama for intent parsing."""
    prompt = request.get("prompt", "")
    language = request.get("language", "en")

    if not prompt:
        raise HTTPException(status_code=400, detail="Prompt is required")

    registry = AgentRegistry()
    ollama_available = await ollama_client.is_available()

    if ollama_available:
        agent_list = registry.list_agents()
        agent_map = {a["agent_id"]: a for a in agent_list}
        agent_descriptions = "\n".join(
            [f"- {a['agent_id']}: {a['agent_name']} — {a['description']}" for a in agent_list]
        )

        system_prompt = (
            f"You are an agent orchestrator for Procurement Flow Specialist BD.\n"
            f"Available agents:\n{agent_descriptions}\n\n"
            f"Given the user's natural language request, determine the single most relevant agent_id to run. "
            f"If multiple agents are needed, pick the primary one. "
            f"Respond with ONLY a JSON object: {{\"agent_id\": \"...\", \"context\": {{key: value}}}}. "
            f"Do NOT include any other text. The context should include relevant parameters inferred from the prompt."
        )

        interpretation = await ollama_client.chat(
            messages=[{"role": "user", "content": prompt}],
            lang=language,
            system_override=system_prompt,
        )

        if interpretation.get("success"):
            content = interpretation["content"]
            try:
                parsed = json.loads(content.strip().strip("`").replace("json", "").strip())
                agent_id = parsed.get("agent_id", "")
                agent_context = parsed.get("context", {})
            except Exception:
                agent_id = ""
                agent_context = {}
        else:
            agent_id = ""
            agent_context = {}
    else:
        prompt_lower = prompt.lower()
        agent_map_simple = {
            "tender": "agent-001-tender-radar",
            "tender acquisition": "agent-002-tender-acquisition",
            "corrigendum": "agent-003-corrigendum-watchdog",
            "pre screen": "agent-038-tender-pre-screener",
            "pre-screen": "agent-038-tender-pre-screener",
            "tender pre": "agent-038-tender-pre-screener",
            "document": "agent-004-document-ai",
            "document prep": "agent-032-document-preparation",
            "boq": "agent-005-boq-intelligence",
            "spec": "agent-006-spec-intelligence",
            "eligibility": "agent-007-eligibility-compliance",
            "risk": "agent-008-risk-intelligence",
            "ppr": "agent-009-ppr-evaluation",
            "ppr dashboard": "agent-037-ppr2025-dashboard",
            "lert": "agent-010-lert-prediction",
            "rate analysis": "agent-011-rate-analysis",
            "rate": "agent-011-rate-analysis",
            "market rate": "agent-012-market-rate-intelligence",
            "sor zone": "agent-044-sor-zone-matcher",
            "zone matcher": "agent-044-sor-zone-matcher",
            "competitor": "agent-013-competitor-intelligence",
            "award": "agent-014-award-intelligence",
            "pricing": "agent-015-competitor-pricing-predictor",
            "moat": "agent-036-moat-slt-analyzer",
            "slt": "agent-036-moat-slt-analyzer",
            "win": "agent-016-win-probability",
            "bid position": "agent-017-bid-position-optimizer",
            "bid assistant": "agent-018-ai-bid-assistant",
            "resource": "agent-019-resource-capacity",
            "app forecast": "agent-042-app-forecast",
            "financial": "agent-021-financial-intelligence",
            "decision": "agent-022-executive-decision",
            "executive": "agent-022-executive-decision",
            "bid no bid": "agent-039-bid-no-bid",
            "no bid": "agent-039-bid-no-bid",
            "client intelligence": "agent-043-client-intelligence",
            "client intel": "agent-043-client-intelligence",
            "egp fill": "agent-020-egp-rate-fill",
            "rate fill": "agent-020-egp-rate-fill",
            "vat": "agent-033-vat-tax-calculator",
            "tax": "agent-033-vat-tax-calculator",
            "submission": "agent-024-submission-validation",
            "tender dashboard": "agent-035-tender-dashboard",
            "report": "agent-023-report-generation",
            "knowledge": "agent-025-knowledge-lake",
            "company brain": "agent-040-company-brain",
            "market brain": "agent-041-market-brain",
            "learn": "agent-026-learning",
            "orchestrator": "agent-027-orchestrator",
            "pipeline": "agent-027-orchestrator",
            "syndicate": "agent-028-syndicate-radar",
            "ra bill": "agent-030-ra-bill-predictor",
            "bill": "agent-030-ra-bill-predictor",
            "vision": "agent-029-vision-intelligence",
        }
        agent_id = ""
        for keyword, aid in agent_map_simple.items():
            if keyword in prompt_lower:
                agent_id = aid
                break
        if not agent_id:
            agent_id = "agent-027-orchestrator"
        agent_context = {"prompt": prompt}

    if not agent_id:
        return {
            "success": True,
            "prompt": prompt,
            "agent_id": None,
            "agent_name": None,
            "language": language,
            "ollama_available": ollama_available,
            "message": "Could not determine which agent to run. Try a more specific request.",
            "result": None,
        }

    agent = registry.get(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")

    agent_context["language"] = language
    agent_context["ollama_available"] = ollama_available
    result = await agent.run(agent_context)

    return {
        "success": True,
        "prompt": prompt,
        "agent_id": agent_id,
        "agent_name": agent.agent_name,
        "language": language,
        "ollama_available": ollama_available,
        "result": result.to_dict(),
        "interpretation": agent_context if not ollama_available else None,
    }


# ── Pipeline Endpoints ────────────────────────────────────────────────────

@router.get("/pipeline/phases")
async def list_pipeline_phases():
    """List all pipeline phases and their agents."""
    from app.agents.orchestrator import PIPELINE_DEFINITION, PipelinePhase
    return {
        "phases": {
            p.value: {
                "agents": PIPELINE_DEFINITION[p],
                "count": len(PIPELINE_DEFINITION[p]),
            }
            for p in PipelinePhase
        }
    }


@router.get("/system/status")
async def system_status():
    """Get full system status including orchestrator state."""
    from app.agents import WorkflowOrchestrator
    registry = AgentRegistry()
    orch = registry.get("agent-027-orchestrator")
    if not isinstance(orch, WorkflowOrchestrator):
        raise HTTPException(status_code=500, detail="Orchestrator not available")
    return await orch.system_status()


@router.get("/circuit-breaker/status")
async def circuit_breaker_status():
    """Get circuit breaker state for all agents."""
    registry = AgentRegistry()
    agents = registry.list_agents()
    result = []
    for agent_info in agents:
        agent = registry.get(agent_info["agent_id"])
        if agent and hasattr(agent, "circuit_breaker_state"):
            result.append({
                "agent_id": agent_info["agent_id"],
                "state": agent.circuit_breaker_state,
                "consecutive_failures": getattr(agent, "_consecutive_failures", 0),
                "open_since": getattr(agent, "_circuit_open_since", None),
            })
    return {"agents": result}


@router.post("/circuit-breaker/reset")
async def reset_circuit_breaker(agent_id: str = Query(None)):
    """Reset circuit breaker for one or all agents."""
    registry = AgentRegistry()
    if agent_id:
        agent = registry.get(agent_id)
        if not agent:
            raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")
        if hasattr(agent, "reset_circuit_breaker"):
            agent.reset_circuit_breaker()
        return {"reset": [agent_id]}
    # Reset all
    reset_ids = []
    for info in registry.list_agents():
        agent = registry.get(info["agent_id"])
        if agent and hasattr(agent, "reset_circuit_breaker"):
            agent.reset_circuit_breaker()
            reset_ids.append(info["agent_id"])
    return {"reset": reset_ids}


@router.get("/repo/facts")
async def repo_facts():
    """Get live repository facts derived from config and runtime state."""
    from app.services.repo_facts import get_repo_facts
    return get_repo_facts()


# ── Tender Radar Endpoint ─────────────────────────────────────────────────

@router.get("/tender-radar")
async def get_tender_radar():
    """Get latest tender radar results (Agent 1)."""
    registry = AgentRegistry()
    radar = registry.get("agent-001-tender-radar")
    if not radar:
        raise HTTPException(status_code=404, detail="Tender Radar agent not found")

    result = await radar.run({})
    return result.to_dict()


# ── Ollama Tender Intelligence (Chat with Tender Context) ─────────────

class TenderIntelligenceRequest(BaseModel):
    query: str
    tender_id: str = ""
    language: str = "en"
    include_tender_data: bool = True


@router.post("/ollama/tender-intelligence")
async def tender_intelligence(req: TenderIntelligenceRequest):
    """Ask Ollama questions about tenders with context from scraped data."""
    from app.core.ollama_client import OllamaClient
    ollama = OllamaClient()

    if not await ollama.is_available():
        return {"success": False, "content": "Ollama not available. Start it with: ollama serve", "engine": "none"}

    context_parts = []
    if req.tender_id:
        tender = await load_tender_snapshot(req.tender_id)
        if tender:
            context_parts.append(f"Tender ID: {tender.get('tender_id', '')}")
            context_parts.append(f"Title: {tender.get('title', '')}")
            context_parts.append(f"Entity: {tender.get('procuring_entity', '')}")
            context_parts.append(f"Deadline: {tender.get('deadline', '')}")
            context_parts.append(f"Value: {tender.get('estimated_value_bdt', 0)} BDT")
            context_parts.append(f"Nature: {tender.get('detected_nature', '')}")
            context_parts.append(f"Status: {tender.get('status', '')}")

    if not context_parts:
        all_t = await load_tender_overview(limit=5000)
        entity_counts = {}
        for t in all_t:
            e = (t.get("pe_office", "") or t.get("procuring_entity", "") or "")[:60]
            entity_counts[e] = entity_counts.get(e, 0) + 1
        top_entities = sorted(entity_counts.items(), key=lambda x: -x[1])[:10]
        context_parts.append(f"Total BWDB tenders monitored: {len(all_t)}")
        context_parts.append("Top procuring entities:")
        for e, c in top_entities:
            context_parts.append(f"  - {e}: {c} tenders")
        upcoming = [t for t in all_t if t.get("award_date", "")]
        upcoming.sort(key=lambda x: x.get("award_date", ""))
        context_parts.append("\nUpcoming deadlines:")
        for t in upcoming[:5]:
            context_parts.append(f"  - {t.get('package_no','')}: {t.get('award_date','')} — {str(t.get('title',''))[:60]}")

    context = "\n".join(context_parts) if context_parts else "No tender data loaded."

    lang_instruction = ""
    if req.language == "bn":
        lang_instruction = "বাংলায় উত্তর দিন। টেন্ডার সংক্রান্ত তথ্য ব্যবহার করে উত্তর দিন।"

    system_prompt = (
        "You are a Tender Intelligence Assistant for Procurement Flow Specialist BD. "
        "You have access to scraped BWDB tender data from the Bangladesh eGP portal. "
        "Answer questions about tenders, deadlines, procuring entities, and tender analysis. "
        "Be precise, reference tender IDs when relevant, and provide actionable insights. "
        f"{lang_instruction}"
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Tender Context:\n{context}\n\nUser Query: {req.query}"},
    ]

    result = await ollama.chat(messages, lang=req.language)
    result["context_used"] = bool(context_parts)
    result["tender_id"] = req.tender_id
    return result


@router.get("/pipeline/status/{task_id}")
async def get_task_status(task_id: str):
    """Poll Celery task status and result."""
    try:
        from app.celery_app import celery_app as celery
        result = celery.AsyncResult(task_id)

        response = {
            "task_id": task_id,
            "status": result.state,
            "ready": result.ready(),
        }

        if result.ready():
            if result.successful():
                response["result"] = result.get()
            else:
                response["error"] = str(result.result) if result.result else "Task failed"

        return response

    except Exception as e:
        return {"task_id": task_id, "status": "UNKNOWN", "error": str(e)}


@router.post("/pipeline/run-async")
async def run_pipeline_async(
    request: Dict[str, Any],
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    """
    Run pipeline in the background via Celery.
    Returns task_id immediately — poll /api/pipeline/status/{task_id} for result.
    """
    from app.workers.tasks import run_pipeline_task

    if not redis_broker_available():
        raise HTTPException(status_code=503, detail="Redis/Celery broker is unavailable")

    mode = request.get("mode", "full")
    phase = request.get("phase")
    agent_ids = request.get("agent_ids")
    context = request.get("context", {}) or {}

    job_id = str(uuid.uuid4())
    queued_context = dict(context)
    queued_context["_agent_job_id"] = job_id
    task = run_pipeline_task.delay(mode=mode, phase=phase,
                                    agent_ids=agent_ids, context=queued_context)
    try:
        await _persist_agent_job(
            db,
            job_id=job_id,
            request_id=task.id,
            agent_id="agent-027-orchestrator",
            context={
                "mode": mode,
                "phase": phase,
                "agent_ids": agent_ids,
                "context": context,
            },
            user=user,
            priority=int(request.get("priority") or context.get("priority") or 0),
        )
    except Exception:
        await db.rollback()
        logger.exception("Failed to persist pipeline job %s for task %s", job_id, task.id)

    return {
        "success": True,
        "job_id": job_id,
        "task_id": task.id,
        "status_url": f"/api/pipeline/status/{task.id}",
        "message": "Pipeline started in background",
    }
