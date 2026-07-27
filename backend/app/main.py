"""
Procurement Flow Specialist BD — Unified API Server
Combines BOQ/SOR comparison engine with 30-Agent Enterprise Operating System.
"""

import asyncio
import importlib
import json
import logging
import os
import socket
import sys
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import Request, FastAPI, HTTPException
from fastapi.responses import JSONResponse, PlainTextResponse
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings as boq_settings
from app.core.helpers import ensure_dir
from app.core.rate_limiter import rate_limit_middleware
from app.core.upload_validation import upload_validation_middleware
from app.sor.sor_service import sor_service

logger = logging.getLogger("procureflow")
_APP_STARTED_AT = time.time()


def _is_public_api_path(path: str) -> bool:
    if not path.startswith("/api"):
        return True
    if path in {"/api", "/api/", "/api/health", "/api/ready", "/api/live"}:
        return True
    for prefix in boq_settings.PUBLIC_API_PREFIXES:
        if path == prefix:
            return True
    return False


def _authenticate_api_request(request: Request) -> Optional[dict]:
    auth = request.headers.get("authorization", "")
    scheme, _, token = auth.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        return None
    try:
        from app.core.security import decode_token
        payload = decode_token(token.strip())
    except Exception:
        return None
    request.state.user = {
        "id": payload.get("sub"),
        "plan": payload.get("plan", "free"),
        "tenant_id": payload.get("tenant_id"),
        "role": payload.get("role", "viewer"),
        "scopes": payload.get("scopes", ["read"]),
    }
    return request.state.user


def _redis_broker_available() -> bool:
    broker_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    try:
        host_port = broker_url.split("://", 1)[-1].split("/", 1)[0]
        host, port_text = host_port.split(":", 1)
        with socket.create_connection((host, int(port_text)), timeout=1):
            return True
    except Exception:
        return False


# ── Agent Registration ────────────────────────────────────────────────────

def register_all_agents(registry, brain=None):
    """Register all 49 active agents."""
    from app.agents import (
        WorkflowOrchestrator,
        TenderRadarAgent,
        TenderAcquisitionAgent,
        CorrigendumWatchdogAgent,
        MaterialPriceCrawlerAgent,
        MaterialMarginAnalyzerAgent,
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
        WhatsAppAutomationAgent,
        PPR2025ComplianceAgent,
        VatTaxCalculatorAgent,
        TenderDocumentAgent,
        TenderPreparationAgent,
        TenderPreScreenerAgent,
        DocumentPreparationAgent,
        TenderDashboardAgent,
        OpeningReportAgent,
        SORZoneMatcherAgent,
        BidNoBidAgent,
        ClientIntelligenceAgent,
        MoatSLTAnalyzerAgent,
        APPForecastAgent,
        PPR2025DashboardAgent,
        CompanyBrainAgent,
        MarketBrainAgent,
        DataQualityValidatorAgent,
        ChangeDetectionAgent,
    )
    agents = [
        TenderRadarAgent(brain=brain), TenderAcquisitionAgent(brain=brain), CorrigendumWatchdogAgent(brain=brain),
        MaterialPriceCrawlerAgent(brain=brain), MaterialMarginAnalyzerAgent(brain=brain), TenderPreScreenerAgent(brain=brain),
        DocumentAIAgent(brain=brain), DocumentPreparationAgent(brain=brain),
        BOQIntelligenceAgent(brain=brain), SpecIntelligenceAgent(brain=brain),
        EligibilityComplianceAgent(brain=brain), RiskIntelligenceAgent(brain=brain), PPREvaluationAgent(brain=brain),
        LERTPredictionAgent(brain=brain), PPR2025DashboardAgent(brain=brain),
        RateAnalysisAgent(brain=brain), MarketRateIntelligenceAgent(brain=brain), SORZoneMatcherAgent(brain=brain),
        CompetitorIntelligenceAgent(brain=brain), AwardIntelligenceAgent(brain=brain), CompetitorPricingPredictorAgent(brain=brain),
        SyndicateRadarAgent(brain=brain), MoatSLTAnalyzerAgent(brain=brain), RABillPredictorAgent(brain=brain),
        WinProbabilityAgent(brain=brain), BidPositionOptimizerAgent(brain=brain),
        APPForecastAgent(brain=brain), ResourceCapacityAgent(brain=brain),
        AIBidAssistantAgent(brain=brain), FinancialIntelligenceAgent(brain=brain), ExecutiveDecisionAgent(brain=brain),
        BidNoBidAgent(brain=brain), ClientIntelligenceAgent(brain=brain),
        EGPRateFillAgent(brain=brain), VatTaxCalculatorAgent(brain=brain),
        SubmissionValidationAgent(brain=brain),
        TenderDocumentAgent(brain=brain), TenderPreparationAgent(brain=brain), TenderDashboardAgent(brain=brain), OpeningReportAgent(brain=brain),
        ReportGenerationAgent(brain=brain),
        KnowledgeLakeAgent(brain=brain), CompanyBrainAgent(brain=brain), MarketBrainAgent(brain=brain),
        LearningAgent(brain=brain),
        VisionIntelligenceAgent(brain=brain),
        WhatsAppAutomationAgent(brain=brain),
        PPR2025ComplianceAgent(brain=brain),
        DataQualityValidatorAgent(brain=brain),
        ChangeDetectionAgent(brain=brain),
        WorkflowOrchestrator(brain=brain),
    ]
    registry.register_many(*agents)
    logger.info(f"Registered {registry.count} agents")
    return registry


def get_registry():
    from app.agents import AgentRegistry
    return AgentRegistry()


# ── App Lifespan ──────────────────────────────────────────────────────────

async def _initialize_agent_runtime(app: FastAPI) -> None:
    try:
        from app.agents import AgentBrain, AgentRegistry

        brain = AgentBrain()
        await brain.start()
        registry = AgentRegistry(brain=brain)
        register_all_agents(registry, brain=brain)

        app.state.brain = brain
        app.state.registry = registry
        app.state.agent_runtime_ready = True

        try:
            import app.api.brain_router as brain_router_mod
            brain_router_mod.set_canonical_brain(brain)
        except Exception as e:
            logger.warning(f"Could not set canonical brain: {e}")
    except Exception as e:
        app.state.agent_runtime_ready = False
        app.state.agent_runtime_error = str(e)
        logger.exception("Agent runtime initialization failed: %s", e)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    logger.info(f"🚀 Starting {boq_settings.APP_NAME} v{boq_settings.VERSION}")
    app.state.brain = None
    app.state.registry = None
    app.state.agent_runtime_ready = False
    app.state.agent_runtime_error = None
    app.state.agent_runtime_task = None
    app.state.api_routers_loaded = False
    app.state.api_routers_error = None
    app.state.api_router_task = None
    app.state.core_api_routers_loaded = False
    
    for d in ['uploads', 'outputs', 'data', 'tenders']:
        ensure_dir(f"{boq_settings.BASE_DIR}/{d}")
    
    # W-001: Alembic is the sole schema management path.
    # init_db() removed — run `alembic upgrade head` for schema management.

    # Initialize RBAC: permissions and system roles (T-035)
    try:
        from app.db.database import get_async_session
        from app.services.rbac_service import RBACService
        async with get_async_session() as db:
            await RBACService.initialize_permissions(db)
            await RBACService.initialize_system_roles(db, tenant_id=None)
            logger.info("✅ RBAC permissions and system roles initialized")
    except Exception as e:
        logger.warning(f"⚠️ RBAC initialization skipped: {e}")

    # Initialize Redis + per-tenant rate limiter (T-036)
    try:
        import redis.asyncio as redis
        from app.core.tenant_rate_limiter import init_tenant_rate_limiter
        from app.core.config import settings as core_settings

        redis_url = core_settings.REDIS_URL or "redis://localhost:6379/0"
        redis_client = redis.from_url(redis_url, decode_responses=True)

        # Test Redis connection
        await redis_client.ping()
        await init_tenant_rate_limiter(redis_client)
        app.state.redis_client = redis_client
        logger.info("✅ Redis connected and tenant rate limiter initialized")
    except Exception as e:
        logger.warning(f"⚠️ Redis/rate-limiter setup skipped: {e}")
        logger.info("   (rate limiter will fail-open: allow all requests)")

    sor_prefer_db = os.getenv("PROCUREFLOW_SOR_DB_ON_STARTUP", "0").strip().lower() in {"1", "true", "yes"}
    sor_service.load_all(prefer_db=sor_prefer_db)
    _include_core_api_routers(app)
    # Await router loading synchronously so routes are available before the first
    # request arrives. Previously this was a background task which caused TestClient
    # tests to hit 404 because the task hadn't completed yet.
    await _load_api_routers(app)
    app.state.api_router_task = None
    if os.getenv("PROCUREFLOW_START_AGENTS_ON_STARTUP", "1").strip().lower() in {"1", "true", "yes"}:
        app.state.agent_runtime_task = asyncio.create_task(_initialize_agent_runtime(app))
    else:
        logger.info("Agent runtime autostart disabled; set PROCUREFLOW_START_AGENTS_ON_STARTUP=1 to enable.")

    try:
        from app.db.base import get_engine
        from app.services.telemetry import configure_telemetry
        app.state.telemetry_enabled = configure_telemetry(app, get_engine())
    except Exception as e:
        logger.warning(f"Telemetry setup skipped: {e}")

    yield
    
    try:
        task = getattr(app.state, "agent_runtime_task", None)
        if task and not task.done():
            task.cancel()
        api_task = getattr(app.state, "api_router_task", None)
        if api_task and not api_task.done():
            api_task.cancel()
        brain = getattr(app.state, "brain", None)
        if brain:
            await brain.stop()
    except Exception as _e:
        logger.debug("Agent shutdown error: %s", _e, exc_info=True)
    try:
        from app.db.base import close_db
        await close_db()
    except Exception as _e:
        logger.debug("DB close error: %s", _e, exc_info=True)


# ── Create App ────────────────────────────────────────────────────────────

app = FastAPI(
    title="Procurement Flow Specialist BD API",
    version=boq_settings.VERSION,
    description="AI Tender Operating System — BOQ/SOR Engine + registry-backed agent orchestration",
    lifespan=lifespan,
)

# Restrict CORS to frontend only in production, allow local dev.
origins = boq_settings.ALLOWED_ORIGINS
if not origins and boq_settings.ENVIRONMENT == "development":
    origins = ["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173"]
    if boq_settings.FRONTEND_URL:
        origins.append(boq_settings.FRONTEND_URL)
elif not origins:
    origins = [boq_settings.FRONTEND_URL] if boq_settings.FRONTEND_URL else []

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID", "X-Tenant-ID", "X-User-ID", "X-CSRF-Token", "X-Api-Key"],
    expose_headers=["X-Request-ID", "Content-Disposition"],
)

# Rate limiting middleware (in-memory, upgrade to Redis for multi-process)
app.middleware("http")(rate_limit_middleware)
app.middleware("http")(upload_validation_middleware)

# Quota enforcement middleware (T-036: check before mutations)
from app.core.quota_middleware import QuotaEnforcementMiddleware
app.add_middleware(QuotaEnforcementMiddleware)


@app.middleware("http")
async def enterprise_request_context(request: Request, call_next):
    request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
    trace_id = request.headers.get("traceparent", "").split("-")[1] if request.headers.get("traceparent", "").count("-") >= 3 else request_id
    request.state.request_id = request_id
    request.state.trace_id = trace_id
    start = time.time()

    if (
        boq_settings.REQUIRE_API_AUTH
        and request.method != "OPTIONS"
        and request.url.path.startswith("/api/")
        and not _is_public_api_path(request.url.path)
        and _authenticate_api_request(request) is None
    ):
        return JSONResponse(
            status_code=401,
            content={"detail": "Authentication required"},
            headers={
                "x-request-id": request_id,
                "www-authenticate": "Bearer",
            },
        )

    # SEC-02/T-015: tenant context for the whole request span — every session
    # acquired below (dependencies, audit write) inherits it via the central
    # contextvar (ADR-007/020).
    from app.db.database import reset_tenant_context, set_tenant_context

    user = getattr(request.state, "user", None) or {}
    request.state.tenant_id = user.get("tenant_id")
    tenant_id = str(user.get("tenant_id") or request.headers.get("x-tenant-id") or "__no_tenant__")
    role = str(user.get("role") or "").lower()
    scopes = set(user.get("scopes") or [])
    tenant_token = set_tenant_context(
        tenant_id, is_superuser=role in {"owner", "admin"} or "*" in scopes
    )
    try:
        response = await call_next(request)
        response.headers["x-request-id"] = request_id
        response.headers.setdefault("x-content-type-options", "nosniff")
        response.headers.setdefault("x-frame-options", "DENY")
        response.headers.setdefault("referrer-policy", "strict-origin-when-cross-origin")
        response.headers.setdefault("permissions-policy", "geolocation=(), microphone=(), camera=()")

        if request.url.path.startswith("/api") and request.method in {"POST", "PUT", "PATCH", "DELETE"}:
            try:
                from app.db.base import get_session_factory
                from app.services.audit_service import log_audit_event
                async with get_session_factory()() as session:
                    await log_audit_event(
                        session,
                        tenant_id=request.headers.get("x-tenant-id"),
                        actor_id=request.headers.get("x-user-id"),
                        actor_type="api",
                        action=f"{request.method} {request.url.path}",
                        resource_type="http_request",
                        resource_id=request_id,
                        status="success" if response.status_code < 400 else "failed",
                        ip_address=request.client.host if request.client else None,
                        user_agent=request.headers.get("user-agent"),
                        request_id=request_id,
                        trace_id=trace_id,
                        metadata={
                            "status_code": response.status_code,
                            "duration_ms": int((time.time() - start) * 1000),
                        },
                    )
                    await session.commit()
            except Exception as exc:
                logger.debug("HTTP audit middleware skipped write: %s", exc)

        # T-017/OBS-01 / W-006: attribute the active trace + record API metrics
        duration_seconds = time.time() - start
        duration_ms = int((time.time() - start) * 1000)
        try:
            from app.services.telemetry import get_metrics, record_span_attributes
            record_span_attributes(
                request_id=request.state.request_id,
                tenant_id=tenant_id,
                path=request.url.path,
                duration_ms=duration_ms,
            )
            metrics = get_metrics()
            if metrics and request.url.path.startswith("/api/"):
                metrics.record_api_request(
                    duration_seconds,
                    method=request.method,
                    path=request.url.path,
                    status=str(response.status_code),
                )
        except Exception as exc:
            logger.debug("Metrics/span recording skipped: %s", exc)

        return response
    finally:
        reset_tenant_context(tenant_token)


# ── Deferred API Router Loading ───────────────────────────────────────────

CORE_V1_ROUTER_MODULES = [
    "auth", "boq", "sor", "competitors", "pricing", "contractors",
    "search", "validation", "reports", "system", "monitoring",
    "government_portals", "rate_analysis", "canonical",
    "crawl",
]

DEFERRED_V1_ROUTER_MODULES = [
    "tenders", "awards", "dashboard", "chat", "epw3", "escalation",
    "market_index", "intelligence", "ppr2025", "analytics", "deptree",
    "predictions", "executive", "agents", "communication", "tender_processing",
    "embeddings", "payments", "webhooks", "contractor_intelligence", "tender_matching",
    "capacity_risk", "advanced_intelligence", "advanced_analytics", "tender_docs",
    "crawler", "graph", "tender_workspace",
]


def _include_v1_module(app: FastAPI, name: str) -> None:
    module = importlib.import_module(f"app.api.v1.{name}")
    app.include_router(module.router, prefix="/api")
    app.include_router(module.router, prefix="/api/v1")


def _include_core_api_routers(app: FastAPI) -> None:
    if getattr(app.state, "core_api_routers_loaded", False):
        return
    for name in CORE_V1_ROUTER_MODULES:
        _include_v1_module(app, name)
    app.state.core_api_routers_loaded = True


def _import_deferred_api_routers():
    routers = []
    for name in DEFERRED_V1_ROUTER_MODULES:
        try:
            module = importlib.import_module(f"app.api.v1.{name}")
            routers.append((name, module.router))
            logger.debug(f"Loaded v1 router: {name}")
        except Exception as e:
            logger.error(f"Failed to load v1 router {name}: {e}")

    try:
        enterprise_v2 = importlib.import_module("app.api.v2.enterprise").router
        logger.debug("Loaded v2 enterprise router")
    except Exception as e:
        logger.error(f"Failed to load enterprise router: {e}")
        raise

    try:
        sso_v2 = importlib.import_module("app.api.v2.sso").router
        logger.debug("Loaded v2 sso router")
    except Exception as e:
        logger.error(f"Failed to load SSO router: {e}")
        sso_v2 = None

    try:
        analytics_v2 = importlib.import_module("app.api.v2.analytics").router
        logger.debug("Loaded v2 analytics router")
    except Exception as e:
        logger.error(f"Failed to load analytics router: {e}")
        analytics_v2 = None

    try:
        benchmarking_v2 = importlib.import_module("app.api.v2.benchmarking").router
        logger.debug("Loaded v2 benchmarking router")
    except Exception as e:
        logger.error(f"Failed to load benchmarking router: {e}")
        benchmarking_v2 = None

    try:
        predictions_v2 = importlib.import_module("app.api.v2.predictions").router
        logger.debug("Loaded v2 predictions router")
    except Exception as e:
        logger.error(f"Failed to load predictions router: {e}")
        predictions_v2 = None

    try:
        market_trends_v2 = importlib.import_module("app.api.v2.market_trends").router
        logger.debug("Loaded v2 market_trends router")
    except Exception as e:
        logger.error(f"Failed to load market_trends router: {e}")
        market_trends_v2 = None

    try:
        contractor_documents_v2 = importlib.import_module("app.api.v2.contractor_documents").router
        logger.debug("Loaded v2 contractor_documents router")
    except Exception as e:
        logger.error(f"Failed to load contractor_documents router: {e}")
        contractor_documents_v2 = None

    try:
        intelligence_enrichment_v2 = importlib.import_module("app.api.v2.intelligence_enrichment").router
        logger.debug("Loaded v2 intelligence_enrichment router")
    except Exception as e:
        logger.error(f"Failed to load intelligence_enrichment router: {e}")
        intelligence_enrichment_v2 = None

    # Phase 2: Tender Management
    try:
        tenders_v2 = importlib.import_module("app.api.v2.tenders").router
        logger.debug("Loaded v2 tenders router")
    except Exception as e:
        logger.error(f"Failed to load tenders router: {e}")
        tenders_v2 = None

    # Phase 2: Document Management
    try:
        documents_v2 = importlib.import_module("app.api.v2.documents").router
        logger.debug("Loaded v2 documents router")
    except Exception as e:
        logger.error(f"Failed to load documents router: {e}")
        documents_v2 = None

    # Phase 2: Team Management
    try:
        team_v2 = importlib.import_module("app.api.v2.team").router
        logger.debug("Loaded v2 team router")
    except Exception as e:
        logger.error(f"Failed to load team router: {e}")
        team_v2 = None

    # Phase 2: Admin Management
    try:
        admin_v2 = importlib.import_module("app.api.v2.admin").router
        logger.debug("Loaded v2 admin router")
    except Exception as e:
        logger.error(f"Failed to load admin router: {e}")
        admin_v2 = None

    # Market intelligence for the Knowledge Platform
    try:
        market_intel_v2 = importlib.import_module("app.api.v2.market_intelligence").router
        logger.debug("Loaded v2 market_intelligence router")
    except Exception as e:
        logger.error(f"Failed to load market_intelligence router: {e}")
        market_intel_v2 = None

    # Phase 3: Missing v2 modules (feedback, pricing, contractor, clauses, roi, rules)
    try:
        feedback_v2 = importlib.import_module("app.api.v2.feedback").router
        logger.debug("Loaded v2 feedback router")
    except Exception as e:
        logger.error(f"Failed to load feedback router: {e}")
        feedback_v2 = None

    try:
        pricing_v2 = importlib.import_module("app.api.v2.pricing").router
        logger.debug("Loaded v2 pricing router")
    except Exception as e:
        logger.error(f"Failed to load pricing router: {e}")
        pricing_v2 = None

    try:
        contractor_v2 = importlib.import_module("app.api.v2.contractor").router
        logger.debug("Loaded v2 contractor router")
    except Exception as e:
        logger.error(f"Failed to load contractor router: {e}")
        contractor_v2 = None

    try:
        clauses_v2 = importlib.import_module("app.api.v2.clauses").router
        logger.debug("Loaded v2 clauses router")
    except Exception as e:
        logger.error(f"Failed to load clauses router: {e}")
        clauses_v2 = None

    try:
        roi_v2 = importlib.import_module("app.api.v2.roi").router
        logger.debug("Loaded v2 roi router")
    except Exception as e:
        logger.error(f"Failed to load roi router: {e}")
        roi_v2 = None

    try:
        rules_v2 = importlib.import_module("app.api.v2.rules").router
        logger.debug("Loaded v2 rules router")
    except Exception as e:
        logger.error(f"Failed to load rules router: {e}")
        rules_v2 = None

    try:
        monitoring_v2 = importlib.import_module("app.api.v2.monitoring").router
        logger.debug("Loaded v2 monitoring router")
    except Exception as e:
        logger.error(f"Failed to load monitoring router: {e}")
        monitoring_v2 = None

    try:
        chat_v2 = importlib.import_module("app.api.v2.chat").router
        logger.debug("Loaded v2 chat router")
    except Exception as e:
        logger.error(f"Failed to load chat router: {e}")
        chat_v2 = None

    try:
        opportunity_v2 = importlib.import_module("app.api.v2.opportunity").router
        logger.debug("Loaded v2 opportunity router")
    except Exception as e:
        logger.error(f"Failed to load opportunity router: {e}")
        opportunity_v2 = None

    try:
        brain_router = importlib.import_module("app.api.brain_router").router
        logger.debug("Loaded brain router")
    except Exception as e:
        logger.error(f"Failed to load brain router: {e}")
        raise

    try:
        websocket_v2 = importlib.import_module("app.api.v2.websocket")
        logger.debug("Loaded v2 websocket router")
    except Exception as e:
        logger.error(f"Failed to load websocket router: {e}")
        websocket_v2 = None

    return routers, enterprise_v2, sso_v2, analytics_v2, benchmarking_v2, predictions_v2, market_trends_v2, contractor_documents_v2, intelligence_enrichment_v2, tenders_v2, documents_v2, team_v2, admin_v2, market_intel_v2, feedback_v2, pricing_v2, contractor_v2, clauses_v2, roi_v2, rules_v2, monitoring_v2, chat_v2, opportunity_v2, brain_router, websocket_v2


async def _load_api_routers(app: FastAPI) -> None:
    if getattr(app.state, "api_routers_loaded", False):
        return
    try:
        routers, enterprise_v2, sso_v2, analytics_v2, benchmarking_v2, predictions_v2, market_trends_v2, contractor_documents_v2, intelligence_enrichment_v2, tenders_v2, documents_v2, team_v2, admin_v2, market_intel_v2, feedback_v2, pricing_v2, contractor_v2, clauses_v2, roi_v2, rules_v2, monitoring_v2, chat_v2, opportunity_v2, brain_router, websocket_v2 = await asyncio.to_thread(_import_deferred_api_routers)
        for _name, router in routers:
            app.include_router(router, prefix="/api")
            app.include_router(router, prefix="/api/v1")
        app.include_router(enterprise_v2, prefix="/api/v2")
        if sso_v2:
            app.include_router(sso_v2, prefix="/api/v2")
        if analytics_v2:
            app.include_router(analytics_v2, prefix="/api/v2")
        if benchmarking_v2:
            app.include_router(benchmarking_v2, prefix="/api/v2")
        if predictions_v2:
            app.include_router(predictions_v2, prefix="/api/v2")
        if market_trends_v2:
            app.include_router(market_trends_v2, prefix="/api/v2")
        if contractor_documents_v2:
            app.include_router(contractor_documents_v2, prefix="/api/v2")
        if intelligence_enrichment_v2:
            app.include_router(intelligence_enrichment_v2, prefix="/api/v2")
        # Phase 2: Tender Management
        if tenders_v2:
            app.include_router(tenders_v2, prefix="/api/v2")
        # Phase 2: Document Management
        if documents_v2:
            app.include_router(documents_v2, prefix="/api/v2")
        # Phase 2: Team Management
        if team_v2:
            app.include_router(team_v2, prefix="/api/v2")
        # Phase 2: Admin Management
        if admin_v2:
            app.include_router(admin_v2, prefix="/api/v2")
        # Knowledge Platform: market intelligence
        if market_intel_v2:
            app.include_router(market_intel_v2, prefix="/api/v2")
        # clean_intel_* datasets (self-contained; not threaded through the tuple)
        try:
            clean_intel_v2 = importlib.import_module("app.api.v2.clean_intel").router
            app.include_router(clean_intel_v2, prefix="/api/v2")
        except Exception as e:
            logger.error(f"Failed to load clean_intel router: {e}")
        # Intelligence v2 — curated endpoints for frontend widgets
        try:
            intel_v2 = importlib.import_module("app.api.v2.intelligence_v2").router
            app.include_router(intel_v2, prefix="/api/v2")
        except Exception as e:
            logger.error(f"Failed to load intelligence_v2 router: {e}")
        # Phase 3: Missing v2 modules
        if feedback_v2:
            app.include_router(feedback_v2, prefix="/api/v2")
        if pricing_v2:
            app.include_router(pricing_v2, prefix="/api/v2")
        if contractor_v2:
            app.include_router(contractor_v2, prefix="/api/v2")
        if clauses_v2:
            app.include_router(clauses_v2, prefix="/api/v2")
        if roi_v2:
            app.include_router(roi_v2, prefix="/api/v2")
        if rules_v2:
            app.include_router(rules_v2, prefix="/api/v2")
        # Phase 3: monitoring, chat, opportunity (V2)
        if monitoring_v2:
            app.include_router(monitoring_v2, prefix="/api/v2")
        if chat_v2:
            app.include_router(chat_v2, prefix="/api/v2")
        if opportunity_v2:
            app.include_router(opportunity_v2, prefix="/api/v2")
        app.include_router(brain_router)
        # Real-time WebSocket/SSE
        if websocket_v2:
            app.include_router(websocket_v2.ws_router, prefix="/ws")
            app.include_router(websocket_v2.sse_router, prefix="/events")
            logger.info("Loaded v2 WebSocket and SSE routers")
        # Intelligence gap-filler — endpoints frontend calls but v1/v2 don't serve
        try:
            gap_router = importlib.import_module("app.api.intelligence_gap_api").router
            app.include_router(gap_router, prefix="/api", tags=["intelligence-gap"])
            logger.info("✅ Intelligence gap API router loaded")
        except Exception as e:
            logger.error(f"Failed to load intelligence_gap_api router: {e}")
        if not getattr(app.state, "catch_all_loaded", False):
            app.add_api_route("/{full_path:path}", catch_all_frontend, methods=["GET"], include_in_schema=False)
            app.state.catch_all_loaded = True
        app.state.api_routers_loaded = True
        logger.info("✅ Deferred API routers loaded: %d v1 modules", len(routers))
    except Exception as exc:
        app.state.api_routers_loaded = False
        app.state.api_routers_error = str(exc)
        logger.exception("API router loading failed: %s", exc)


@app.get("/health", include_in_schema=False)
async def health_root():
    return {"status": "ok", "service": "procureflow"}


# ── Probe helpers (T-009/API-02) — cheap, bounded, never raise ────────────

# Per-check timeout for local dependencies
_PROBE_TIMEOUT_S = float(os.environ.get("PROBE_CHECK_TIMEOUT_S", "1.0"))
_CELERY_PROBE_TIMEOUT_S = float(os.environ.get("CELERY_PROBE_TIMEOUT_S", "3.0"))
# Checks that gate /api/ready (503 until all true); others are informational
_READY_GATING = tuple(
    p.strip() for p in os.environ.get(
        "READINESS_GATING_CHECKS", "database,redis,celery,api_routers_loaded"
    ).split(",") if p.strip()
)


async def _timed_probe(coro, timeout: float = _PROBE_TIMEOUT_S) -> dict:
    """Run a dependency check with a bounded timeout; report ok + latency."""
    started = time.perf_counter()
    try:
        detail = await asyncio.wait_for(coro, timeout=timeout)
        return {"ok": True, "latency_ms": round((time.perf_counter() - started) * 1000, 1), **(detail or {})}
    except Exception as exc:
        return {
            "ok": False,
            "latency_ms": round((time.perf_counter() - started) * 1000, 1),
            "error": str(exc)[:200] or type(exc).__name__,
        }


async def _probe_database() -> dict:
    from app.db.database import check_database_health, get_engine, using_pgbouncer
    health = await check_database_health()
    if health.get("status") != "healthy":
        raise RuntimeError(health.get("error", "database unhealthy"))
    pool = get_engine().pool
    return {"via_pgbouncer": using_pgbouncer(), "pool": {
        "size": pool.size(), "checked_out": pool.checkedout(),
        "overflow": pool.overflow(),
    }}


def _redis_client():
    import redis.asyncio as aioredis
    url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
    return aioredis.from_url(url, socket_connect_timeout=_PROBE_TIMEOUT_S, socket_timeout=_PROBE_TIMEOUT_S)


async def _probe_redis() -> dict:
    client = _redis_client()
    try:
        await client.ping()
        return {}
    finally:
        await client.aclose()


async def _probe_celery() -> dict:
    """Broker reachability + queue depths + live worker count."""
    client = _redis_client()
    try:
        queues = {}
        for queue in ("celery", "high", "default", "low"):
            queues[queue] = int(await client.llen(queue))
        # Worker liveness via Celery control inspect (blocking → offload to thread)
        alive_workers = 0
        try:
            from app.celery_app import celery_app

            def _ping():
                inspector = celery_app.control.inspect(timeout=2.0)
                return inspector.ping() or {}

            alive_workers = len(await asyncio.to_thread(_ping))
            metrics = get_metrics_safe()
            set_workers_alive = getattr(metrics, "set_celery_workers_alive", None)
            if set_workers_alive:
                set_workers_alive(alive_workers)
        except Exception:
            metrics = get_metrics_safe()
            set_workers_alive = getattr(metrics, "set_celery_workers_alive", None)
            if set_workers_alive:
                set_workers_alive(0)
        if alive_workers < 1:
            raise RuntimeError("no Celery workers responded")
        return {"queues": queues, "alive_workers": alive_workers}
    finally:
        await client.aclose()


def get_metrics_safe():
    try:
        from app.services.telemetry import get_metrics
        return get_metrics()
    except Exception:
        return None


async def _probe_agents() -> dict:
    ready = bool(getattr(app.state, "agent_runtime_ready", False))
    registry = getattr(app.state, "registry", None)
    count = int(getattr(registry, "count", 0) or 0)
    try:
        from app.services.telemetry import get_metrics
        m = get_metrics()
        if m:
            m.set_agent_count(count)
    except Exception as _e:
        logger.debug("Agent metrics error: %s", _e, exc_info=True)
    if not ready:
        raise RuntimeError(getattr(app.state, "agent_runtime_error", None) or "agent runtime not ready")
    return {"registered_agents": count}


async def _probe_minio() -> dict:
    """MinIO/S3 object-storage reachability via a bucket existence check."""
    storage_backend = os.getenv("STORAGE_BACKEND", "local").strip().lower()
    if storage_backend != "minio":
        raise RuntimeError("storage backend is not minio")
    from app.services.storage_service import storage_service
    client = storage_service._get_client()
    bucket = storage_service.bucket
    if not client.bucket_exists(bucket):
        raise RuntimeError(f"minio bucket {bucket} missing")
    return {"bucket": bucket}


@app.get("/api/health/minio", include_in_schema=False)
async def api_health_minio():
    result = await _timed_probe(_probe_minio())
    try:
        from app.services.telemetry import get_metrics
        m = get_metrics()
        if m:
            m.set_minio_up(bool(result.get("ok")))
    except Exception as _e:
        logger.debug("MinIO metrics error: %s", _e, exc_info=True)
    return {"dependency": "minio", **result}


@app.get("/api/ready", include_in_schema=False)
async def api_readiness():
    """Kubernetes readiness probe — 503 until every gating check passes.

    Gating (READINESS_GATING_CHECKS): database, redis, celery, api_routers_loaded.
    agents is reported but non-gating (loads in background after startup).
    OTel (W-006, criterion 8): when OTEL_ENABLED, telemetry init is added to
    the gating set so /api/ready fails if instrumentation failed to start.
    """
    otel_enabled = os.getenv("OTEL_ENABLED", "true").strip().lower() in {"1", "true", "yes", "on"}
    otel_ok = bool(getattr(app.state, "telemetry_enabled", False)) if otel_enabled else True

    db, redis_check, celery_check, agents = await asyncio.gather(
        _timed_probe(_probe_database()),
        _timed_probe(_probe_redis()),
        _timed_probe(_probe_celery(), _CELERY_PROBE_TIMEOUT_S),
        _timed_probe(_probe_agents()),
    )
    checks: dict[str, Any] = {
        "database": db,
        "redis": redis_check,
        "celery": celery_check,
        "agents": agents,
        "api_routers_loaded": {"ok": bool(getattr(app.state, "api_routers_loaded", False))},
        "core_api_routers_loaded": {"ok": bool(getattr(app.state, "core_api_routers_loaded", False))},
        "otel": {"ok": otel_ok, "enabled": otel_enabled},
    }
    gating = list(_READY_GATING) + (["otel"] if otel_enabled else [])
    all_ready = all(checks.get(name, {}).get("ok", False) for name in gating)
    body = {"status": "ready" if all_ready else "not_ready", "gating": gating, "checks": checks}
    if not all_ready:
        return JSONResponse(status_code=503, content=body)
    return body


@app.get("/api/live", include_in_schema=False)
async def api_liveness():
    """Kubernetes liveness probe — minimal, always returns OK if process alive."""
    return {"status": "alive"}


@app.get("/api/health/db", include_in_schema=False)
async def api_health_db():
    result = await _timed_probe(_probe_database())
    try:
        from app.services.telemetry import get_metrics
        m = get_metrics()
        if m:
            m.set_db_up(bool(result.get("ok")))
    except Exception as _e:
        logger.debug("DB metrics error: %s", _e, exc_info=True)
    return {"dependency": "postgresql", **result}


@app.get("/api/health/redis", include_in_schema=False)
async def api_health_redis():
    result = await _timed_probe(_probe_redis())
    try:
        from app.services.telemetry import get_metrics
        m = get_metrics()
        if m:
            m.set_redis_up(bool(result.get("ok")))
    except Exception as _e:
        logger.debug("Redis metrics error: %s", _e, exc_info=True)
    return {"dependency": "redis", **result}


@app.get("/api/health/celery", include_in_schema=False)
async def api_health_celery():
    result = await _timed_probe(_probe_celery(), _CELERY_PROBE_TIMEOUT_S)
    try:
        from app.services.telemetry import get_metrics
        m = get_metrics()
        if m:
            m.set_redis_up(True)  # broker reachable == redis up
            for queue, depth in (result.get("queues") or {}).items():
                m.set_celery_queue_depth(queue, int(depth))
    except Exception as _e:
        logger.debug("Celery metrics error: %s", _e, exc_info=True)
    return {"dependency": "celery-broker", **result}


@app.get("/api/health/agents", include_in_schema=False)
async def api_health_agents():
    result = await _timed_probe(_probe_agents())
    try:
        from app.services.telemetry import get_metrics
        m = get_metrics()
        if m:
            m.set_agent_runtime_ready(bool(result.get("ok")))
    except Exception as _e:
        logger.debug("Agent runtime metrics error: %s", _e, exc_info=True)
    return {"dependency": "agent-runtime", **result}


async def _probe_extraction_agents() -> dict:
    """Verify Phase 2 document extraction agents are available."""
    try:
        from app.agents import (
            BOQIntelligenceAgent,
            SpecIntelligenceAgent,
            DocumentAIAgent,
        )

        agents = {
            "BOQIntelligenceAgent": BOQIntelligenceAgent(),
            "SpecIntelligenceAgent": SpecIntelligenceAgent(),
            "DocumentAIAgent": DocumentAIAgent(),
        }
        return {
            "available_agents": len(agents),
            "agent_types": list(agents.keys()),
        }
    except Exception as e:
        raise RuntimeError(f"Extraction agents not available: {str(e)}")


@app.get("/api/health/extraction-agents", include_in_schema=False)
async def api_health_extraction_agents():
    """Health check for document extraction agents."""
    result = await _timed_probe(_probe_extraction_agents())
    return {"dependency": "extraction-agents", **result}


@app.get("/api/health/replica", include_in_schema=False, tags=["health"])
async def api_health_replica():
    """T-034 (ENT-07): replica replication lag.

    Returns lag in seconds from each standby reported via pg_stat_replication.
    A ``max_lag_seconds`` > REPLICA_LAG_WARN_SECONDS triggers a WARNING in logs.
    The endpoint is always HTTP 200 — callers can inspect ``ok`` and ``max_lag_seconds``.
    """
    from app.db.database import check_replica_lag
    from app.core.config import settings

    lag_info = await check_replica_lag()
    max_lag = lag_info.get("max_lag_seconds")
    warn_threshold = settings.REPLICA_LAG_WARN_SECONDS
    ok = True
    if max_lag is not None and max_lag > warn_threshold:
        logger.warning(
            "Replica lag %.1fs exceeds threshold %ds",
            max_lag,
            warn_threshold,
        )
        ok = False
    return {
        "dependency": "read-replica",
        "ok": ok,
        "has_replica": lag_info.get("has_replica"),
        "max_lag_seconds": max_lag,
        "replication_slots": lag_info.get("replication_slots", []),
        "lag_warn_threshold_seconds": warn_threshold,
    }


@app.get("/metrics", response_class=PlainTextResponse, include_in_schema=False)
async def prometheus_metrics():
    """Prometheus scrape endpoint — all domain + health metrics (W-006).

    Exposes every procureflow_* series registered on the default REGISTRY:
    API latency/throughput (per path/method/status), agent execution, Celery
    task duration, SOR match latency, knowledge store size, infra health
    gauges (DB/Redis/MinIO/Celery) and runtime flags.
    """
    try:
        from prometheus_client import REGISTRY, generate_latest
        from app.services.telemetry import get_metrics

        metrics = get_metrics()
        if metrics:
            # Keep runtime flags in sync with live app state before scrape
            try:
                metrics.set_api_routers_loaded(bool(getattr(app.state, "api_routers_loaded", False)))
                metrics.set_agent_runtime_ready(bool(getattr(app.state, "agent_runtime_ready", False)))
                metrics.set_uptime(max(0, time.time() - _APP_STARTED_AT))
            except Exception:
                logger.debug("metrics flag sync skipped")
        return PlainTextResponse(
            generate_latest(REGISTRY).decode("utf-8"),
            media_type="text/plain; version=0.0.4; charset=utf-8",
        )
    except ImportError:
        return PlainTextResponse("Prometheus client not installed\n")


# ── Static File Serving (SPA Frontend) ────────────────────────────────────

from fastapi.staticfiles import StaticFiles
_static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(_static_dir):
    app.mount("/static", StaticFiles(directory=_static_dir, html=True), name="static")


# ── Root Endpoints ────────────────────────────────────────────────────────

@app.get("/")
async def root():
    import os
    static_file = os.path.join(os.path.dirname(__file__), "static", "index.html")
    if os.path.exists(static_file):
        from fastapi.responses import HTMLResponse
        with open(static_file, encoding="utf-8") as f:
            return HTMLResponse(f.read())
    return {
        "app": boq_settings.APP_NAME,
        "version": boq_settings.VERSION,
        "status": "running",
    }


# ── SPA Catch-all (must be LAST) ──────────────────────────────────────────

async def catch_all_frontend(full_path: str):
    """Serve SPA for non-API routes."""
    if full_path.startswith("api/") or full_path.startswith("docs") or full_path.startswith("openapi"):
        raise HTTPException(status_code=404)
    import os
    static_file = os.path.join(os.path.dirname(__file__), "static", "index.html")
    if os.path.exists(static_file):
        from fastapi.responses import HTMLResponse
        with open(static_file, encoding="utf-8") as f:
            return HTMLResponse(f.read())
    raise HTTPException(status_code=404)


# ── Run ───────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    
    # JSON structured logging for production (ELK/Loki ingestion)
    log_format = os.getenv("LOG_FORMAT", "text")
    if log_format == "json":
        import json as _json
        class JsonFormatter(logging.Formatter):
            def format(self, record):
                log_entry = {
                    "ts": self.formatTime(record),
                    "level": record.levelname,
                    "logger": record.name,
                    "msg": record.getMessage(),
                    "module": record.module,
                    "func": record.funcName,
                    "line": record.lineno,
                }
                if record.exc_info and record.exc_info[0]:
                    log_entry["exc"] = self.formatException(record.exc_info)
                return _json.dumps(log_entry, default=str)
        handler = logging.StreamHandler()
        handler.setFormatter(JsonFormatter())
        logging.getLogger().handlers = [handler]
        logging.getLogger().setLevel(logging.INFO)
    else:
        logging.basicConfig(
            level=logging.DEBUG if boq_settings.ENVIRONMENT == "development" else logging.INFO,
            format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        )
    
    host = os.getenv("PROCUREFLOW_HOST", "0.0.0.0")
    port = int(os.getenv("PROCUREFLOW_PORT", "8000"))
    reload_enabled = os.getenv("PROCUREFLOW_RELOAD", "").strip().lower() in {"1", "true", "yes", "on"}
    
    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        reload=reload_enabled,
        log_level="info",
    )
