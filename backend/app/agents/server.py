"""
Procurement Flow Specialist BD — Server Entry Point
FastAPI server exposing the agent system as a REST API.

New services initialized at startup:
  - LLMService (Unified LLM: Ollama primary, OpenAI/Anthropic fallback)
  - AgentMemoryService (Persistent agent state + conversations + knowledge graph)
  - VectorDBService (ChromaDB semantic search + RAG)
"""

import logging
import inspect
from typing import Any, Dict

import uvicorn
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from . import (
    AgentBrain,
    AgentRegistry,
    WorkflowOrchestrator,
    TenderRadarAgent,
    TenderAcquisitionAgent,
    CorrigendumWatchdogAgent,
    DocumentAIAgent,
    BOQIntelligenceAgent,
    SpecIntelligenceAgent,
    EligibilityComplianceAgent,
    RiskIntelligenceAgent,
    PPREvaluationAgent,
    LERTPredictionAgent,
    RateAnalysisAgent,
    MarketRateIntelligenceAgent,
    CompetitorIntelligenceAgent,
    AwardIntelligenceAgent,
    SyndicateRadarAgent,
    RABillPredictorAgent,
    CompetitorPricingPredictorAgent,
    WinProbabilityAgent,
    BidPositionOptimizerAgent,
    AIBidAssistantAgent,
    ResourceCapacityAgent,
    FinancialIntelligenceAgent,
    ExecutiveDecisionAgent,
    EGPRateFillAgent,
    SubmissionValidationAgent,
    ReportGenerationAgent,
    KnowledgeLakeAgent,
    LearningAgent,
    VisionIntelligenceAgent,
    # New services
    LLMService,
    AgentMemoryService,
    VectorDBService,
    RAGService,
)
from .runner import AGENT_CLASSES
from app.core.config import settings
from app.core.security import get_current_user

logger = logging.getLogger("procureflow.server")
MAX_AGENT_CONTEXT_BYTES = 2_000_000
MAX_LLM_PROMPT_CHARS = 20_000

# ── Global service instances (initialized at startup) ──────────────────
brain: AgentBrain | None = None
registry = AgentRegistry()
llm_service: LLMService | None = None
memory_service: AgentMemoryService | None = None
vector_db_service: VectorDBService | None = None
rag_service: RAGService | None = None


def _assert_payload_size(payload: Any, max_bytes: int = MAX_AGENT_CONTEXT_BYTES) -> None:
    """Reject oversized agent payloads before they reach agents or LLMs."""
    import json

    try:
        size = len(json.dumps(payload, default=str).encode("utf-8"))
    except Exception:
        size = len(str(payload).encode("utf-8"))
    if size > max_bytes:
        raise HTTPException(status_code=413, detail=f"Payload exceeds {max_bytes} bytes")


def _build_agent(cls, service_kwargs: Dict[str, Any]):
    signature = inspect.signature(cls)
    params = signature.parameters
    if any(p.kind == inspect.Parameter.VAR_KEYWORD for p in params.values()):
        return cls(**service_kwargs)
    accepted = {name for name in params if name != "self"}
    return cls(**{key: value for key, value in service_kwargs.items() if key in accepted})


def init_services():
    """Initialize all intelligence services."""
    global llm_service, memory_service, vector_db_service, rag_service, brain

    logger.info("Initializing agent intelligence services...")

    # 0. Agent Brain (must exist before agents are registered)
    try:
        brain = AgentBrain()
        AgentRegistry(brain=brain)
        logger.info("✓ AgentBrain initialized")
    except Exception as e:
        logger.error("✗ AgentBrain failed: %s", e)
        brain = None

    # 1. LLM Service (most visible win)
    try:
        llm_service = LLMService()
        logger.info("✓ LLMService initialized: %s", llm_service.get_stats())
    except Exception as e:
        logger.error("✗ LLMService failed: %s", e)
        llm_service = None

    # 2. Agent Memory Service
    try:
        memory_service = AgentMemoryService(redis_url=settings.REDIS_URL)
        logger.info("✓ AgentMemoryService initialized")
    except Exception as e:
        logger.error("✗ AgentMemoryService failed: %s", e)
        memory_service = None

    # 3. Vector DB Service
    try:
        vector_db_service = VectorDBService()
        logger.info("✓ VectorDBService initialized: %s", vector_db_service.is_available)
    except Exception as e:
        logger.error("✗ VectorDBService failed: %s", e)
        vector_db_service = None

    # 4. RAG Service (depends on vector_db + llm)
    if vector_db_service and llm_service:
        try:
            rag_service = RAGService(vector_db=vector_db_service, llm_service=llm_service)
            logger.info("✓ RAGService initialized")
        except Exception as e:
            logger.error("✗ RAGService failed: %s", e)
            rag_service = None


def register_all_agents():
    """Register all agents with services injected."""
    if registry.count:
        return

    # Common service kwargs for all agents
    service_kwargs = {
        "brain": brain,
        "memory": memory_service,
        "llm_service": llm_service,
        "vector_db": vector_db_service,
    }

    agents = [_build_agent(cls, service_kwargs) for cls in AGENT_CLASSES]
    registry.register_many(*agents)
    logger.info(f"Registered {len(agents)} agents with intelligence services")


app = FastAPI(
    title="Procurement Flow Specialist BD API",
    version=settings.VERSION,
    description="AI Tender Operating System — Agent Registry & Orchestration with LLM + Memory + Vector DB",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def _startup():
    """Initialize services and register all agents on startup."""
    init_services()
    if brain is not None:
        await brain.start()
    register_all_agents()


@app.get("/")
async def root():
    return {
        "app": settings.APP_NAME,
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
    }


@app.get("/api/health")
async def health():
    """Health check including service status."""
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": settings.VERSION,
        "agents_registered": registry.count,
        "services": {
            "llm": llm_service.get_stats() if llm_service else None,
            "memory": await memory_service.get_stats() if memory_service else None,
            "vector_db": await vector_db_service.get_stats() if vector_db_service else None,
            "rag": rag_service is not None,
        },
    }


@app.get("/api/agents")
async def list_agents():
    return {"total": registry.count, "agents": registry.list_agents()}


@app.get("/api/agents/{agent_id}")
async def get_agent(agent_id: str):
    agent = registry.get(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")
    return agent.info()


@app.post("/api/agents/{agent_id}/run")
async def run_agent(
    agent_id: str,
    context: Dict[str, Any] | None = None,
    user: Dict[str, Any] = Depends(get_current_user),
):
    context = context or {}
    _assert_payload_size(context)
    result = await registry.run_agent(agent_id, context)
    if result.status.value == "failed":
        raise HTTPException(status_code=500, detail=result.to_dict())
    return result.to_dict()


@app.post("/api/pipeline/run")
async def run_pipeline(
    request: Dict[str, Any],
    user: Dict[str, Any] = Depends(get_current_user),
):
    _assert_payload_size(request)
    orch = registry.get("agent-027-orchestrator")
    if not orch:
        raise HTTPException(status_code=500, detail="Orchestrator not found")
    ctx = request.get("context", {})
    ctx["mode"] = request.get("mode", "full")
    if request.get("phase"): ctx["phase"] = request["phase"]
    if request.get("agent_ids"): ctx["agent_ids"] = request["agent_ids"]
    result = await orch.run(ctx)
    return result.to_dict()


@app.get("/api/system/status")
async def system_status():
    orch = registry.get("agent-027-orchestrator")
    if not isinstance(orch, WorkflowOrchestrator):
        raise HTTPException(status_code=500, detail="Orchestrator not available")
    return await orch.system_status()


@app.get("/api/pipeline/phases")
async def list_phases():
    from .orchestrator import PIPELINE_DEFINITION, PipelinePhase
    return {
        "phases": {
            p.value: {"agents": PIPELINE_DEFINITION[p], "count": len(PIPELINE_DEFINITION[p])}
            for p in PipelinePhase
        }
    }


# ── New Intelligence Service Endpoints ────────────────────────────────

@app.get("/api/intelligence/llm/status")
async def llm_status():
    """Get LLM service status and available providers."""
    if not llm_service:
        raise HTTPException(status_code=503, detail="LLM service not available")
    return llm_service.get_stats()


@app.post("/api/intelligence/llm/generate")
async def llm_generate(
    request: Dict[str, Any],
    user: Dict[str, Any] = Depends(get_current_user),
):
    """Direct LLM generation endpoint."""
    if not llm_service:
        raise HTTPException(status_code=503, detail="LLM service not available")
    prompt = request.get("prompt", "")
    if not prompt:
        raise HTTPException(status_code=400, detail="prompt is required")
    if len(prompt) > MAX_LLM_PROMPT_CHARS:
        raise HTTPException(status_code=413, detail=f"prompt exceeds {MAX_LLM_PROMPT_CHARS} characters")
    response = await llm_service.generate(
        prompt=prompt,
        provider=request.get("provider", "auto"),
        model=request.get("model"),
        temperature=request.get("temperature", 0.7),
        max_tokens=request.get("max_tokens", 2048),
        system_prompt=request.get("system_prompt", ""),
    )
    return {
        "content": response.content,
        "model": response.model,
        "provider": response.provider,
        "tokens_used": response.tokens_used,
        "latency_ms": response.latency_ms,
    }


@app.post("/api/intelligence/llm/analyze-bid")
async def llm_analyze_bid(
    request: Dict[str, Any],
    user: Dict[str, Any] = Depends(get_current_user),
):
    """LLM-powered bid analysis endpoint."""
    if not llm_service:
        raise HTTPException(status_code=503, detail="LLM service not available")
    context = request.get("context", {})
    tender = request.get("tender", {})
    _assert_payload_size({"context": context, "tender": tender})
    result = await llm_service.analyze_bid(context, tender)
    return result


@app.get("/api/intelligence/memory/stats")
async def memory_stats():
    """Get agent memory statistics."""
    if not memory_service:
        raise HTTPException(status_code=503, detail="Memory service not available")
    return await memory_service.get_stats()


@app.get("/api/intelligence/vector-db/stats")
async def vector_db_stats():
    """Get vector DB statistics."""
    if not vector_db_service:
        raise HTTPException(status_code=503, detail="Vector DB service not available")
    return await vector_db_service.get_stats()


@app.post("/api/intelligence/rag/query")
async def rag_query(
    request: Dict[str, Any],
    user: Dict[str, Any] = Depends(get_current_user),
):
    """RAG query endpoint."""
    if not rag_service:
        raise HTTPException(status_code=503, detail="RAG service not available")
    query = request.get("query", "")
    if not query:
        raise HTTPException(status_code=400, detail="query is required")
    if len(query) > MAX_LLM_PROMPT_CHARS:
        raise HTTPException(status_code=413, detail=f"query exceeds {MAX_LLM_PROMPT_CHARS} characters")
    result = await rag_service.answer(
        query=query,
        collection=request.get("collection", "tender_documents"),
        n_results=request.get("n_results", 5),
    )
    return result


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.DEBUG if settings.ENVIRONMENT == "development" else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    uvicorn.run(
        "app.agents.server:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.ENVIRONMENT == "development",
    )
