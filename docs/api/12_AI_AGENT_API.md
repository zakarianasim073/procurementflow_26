# AI Agent API Contract

**Router**: `/api/v1/agents`  
**Tags**: `agents`  
**Auth**: JWT (tenant-scoped)

---

## Overview

Enterprise AI Agent Orchestration Layer providing **agent-as-a-service** API for 49+ specialized AI agents. Core to **AgentBrain architecture** and **intelligent automation** across tender lifecycle (discovery, analysis, compliance, pricing, reporting).

**Agent Categories**:
- **Discovery** (3): TenderRadar, Acquisition, CorrigendumWatchdog
- **Acquisition** (7): DocumentAI, Preparation, OpeningReport, Validation, Dashboard, Document, Preparation
- **Evaluation** (7): DataQuality, EligibilityCompliance, LERTPrediction, PPREvaluation, PPR2025Compliance, PPR2025Dashboard, RiskIntelligence
- **Intelligence** (6): APPForecast, AwardIntelligence, BOQIntelligence, ChangeDetection, ResourceCapacity, SpecIntelligence
- **Competitor** (6): BidPositionOptimizer, CompetitorIntelligence, CompetitorPricingPredictor, MoatSLTAnalyzer, SyndicateRadar, WinProbability
- **Pricing** (6): EGPRateFill, MarketRateIntelligence, RABillPredictor, RateAnalysis, SORZoneMatcher, VatTaxCalculator
- **Decision** (5): AIBidAssistant, BidNoBid, ClientIntelligence, ExecutiveDecision, FinancialIntelligence
- **Knowledge** (4): CompanyBrain, MarketBrain, KnowledgeLake, ReportGeneration
- **Learning** (1): Learning

**Total**: 49 agents with **Orchestrator** (agent-027) as central coordinator.

---

## Endpoint Catalog

| Method | Path | Purpose | Auth |
|--------|------|---------|------|
| GET | `/agents` | List all registered agents (metadata) | JWT |
| GET | `/agents/{agent_id}` | Get agent details by ID | JWT |
| GET | `/agent-results/recent` | Recent agent execution results | JWT |
| POST | `/agents/{agent_id}/run` | Run agent synchronously (long-running → async) | JWT |
| POST | `/agents/whatsapp-automation/run` | Run WhatsApp automation agent | JWT |
| POST | `/agents/{agent_id}/run-async` | Run agent in background via Celery | JWT |
| POST | `/agents/egp/login` | Test eGP portal login credentials | JWT |
| POST | `/agents/egp/search` | Search tenders on eGP portal | JWT |
| POST | `/agents/ollama-run` | Natural language agent selection | JWT |
| GET | `/pipeline/phases` | List all pipeline phases and agents | JWT |
| GET | `/system/status` | Full system status including orchestrator | JWT |
| GET | `/repo/facts` | Get live repository facts | Public |
| GET | `/tender-radar` | Get tender radar results | JWT |
| POST | `/ollama/tender-intelligence` | Ask Ollama with tender context | Public |

---

## Request/Response Schemas

### `GET /agents`

**Response (200)**
```json
{
  "agents": [
    {
      "agent_id": "agent-001-tender-radar",
      "agent_name": "Tender Radar Agent",
      "description": "Crawls e-GP, identifies tender opportunities, matches criteria",
      "category": "discovery",
      "status": "idle|ready|running|error",
      "capabilities": ["scan", "filter", "match"],
      "dependencies": [],
      "timeout_seconds": 300,
      "retry_policy": { "max_attempts": 3, "delay_ms": 1000 },
      "monitoring": { "metrics": ["records_processed", "processing_time"] },
      "created_at": "2026-01-15T10:00:00Z",
      "updated_at": "2026-07-21T12:00:00Z"
    }
  ],
  "total": 49,
  "categories": {
    "discovery": 3,
    "acquisition": 7,
    "evaluation": 7,
    "intelligence": 6,
    "competitor": 6,
    "pricing": 6,
    "decision": 5,
    "knowledge": 4,
    "learning": 1
  }
}
```

### `GET /agents/{agent_id}`

**Response (200)**
```json
{
  "agent_id": "agent-025-knowledge-lake",
  "agent_name": "Knowledge Lake Agent",
  "description": "Manages knowledge storage, retrieval, and lifecycle across brain cache",
  "category": "knowledge",
  "status": "ready",
  "capabilities": ["ingest", "index", "retrieve", "share"],
  "dependencies": ["Redis", "PostgreSQL", "AgentBrain"],
  "timeout_seconds": 1800,
  "retry_policy": { "max_attempts": 1, "delay_ms": 5000 },
  "monitoring": { "metrics": ["cache_hits", "storage_size", "query_latency"] },
  "prompt_template": "### Role: Knowledge Lake Agent",
  "health_check\": {
    "redis_connected": true,
    "pg_connected": true,
    "brain_available": true,
    "last_sync": "2026-07-21T11:30:00Z"
  },
  "created_at": "2026-01-15T10:00:00Z",
  "updated_at": "2026-07-21T12:00:00Z"
}
```

### `GET /agent-results/recent`

**Query Parameters**
| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `limit` | int | 12 | Max results (1-50) |

**Response (200)**
```json
{
  "total": 12,
  "results": [
    {
      "run_id": "run-12345",
      "source": "database",
      "timestamp": "2026-07-21T10:45:30Z",
      "tender_id": "1290886",
      "agent_id": "agent-002-tender-acquisition",
      "agent_name": "Tender Acquisition Agent",
      "status": "success",
      "output": {
        "tenders_scanned": 1247,
        "tenders_matched": 89,
        "documents_downloaded": 156
      },
      "error": "",
      "execution_time_ms": 342,
      "confidence_score": 0.92
    }
  ]
}
```

### `POST /agents/{agent_id}/run`

**Request**
```json
{
  "context": {
    "tender_id": "1290886",
    "action": "extract",
    "priority": "high",
    "timeout_seconds": 180
  },
  "language": "en",
  "force_sync": false
}
```

**Response (200 or 202)**
```json
{
  "success": true,
  "agent_id": "agent-025-knowledge-lake",
  "agent_name": "Knowledge Lake Agent",
  "language": "en",
  "ollama_available": false,
  "result": {
    "status": "success",
    "output": {"knowledge_stored": 1, "cache_hits": 12},
    "metrics": {"processing_time_ms": 1250},
    "recommendations": []
  },
  "interpretation": {
    "determined_agent": "agent-025-knowledge-lake",
    "context_used": {
      "tender_id": "1290886",
      "action": "extract"
    },
    "reasoning": "Extracted knowledge from agent-002"
  } if ollama_available else null
}
```

**Response (202 - Long Running Agent)**
```json
{
  "success": true,
  "async": true,
  "job_id": "uuid",
  "task_id": "uuid",
  "status_url": "/api/pipeline/status/uuid",
  "message": "agent-002-tender-acquisition is long-running; dispatched to background",
  "ready_for_poll": true
}
```

### `POST /agents/whatsapp-automation/run`

**Request**
```json
{
  "action": "send_summary",
  "phone": "+8801712345678",
  "message": "Daily tender summary: 12 tenders, 3 high-value opportunities",
  "tender_id": "1290886",
  "language": "bn",
  "tenders": [
    {
      "tender_id": "1290886",
      "title": "Construction of Bridge",
      "procuring_entity": "BWDB Dhaka Division",
      "estimated_value_bdt": 45000000,
      "deadline": "2026-08-15",
      "win_probability": 0.71
    }
  ]
}
```

**Response (200)
```json
{
  "success": true,
  "result": {
    "message_id": "msg-12345",
    "status": "sent",
    "delivered": true,
    "sent_at": "2026-07-21T10:46:15Z",
    "response": "Message delivered successfully"
  }
}
```

### `POST /agents/ollama-run`

**Request**
```json
{
  "prompt": "Find tenders for bridge construction in Chattogram district",
  "language": "en",
  "max_agents": 3
}
```

**Response (200)**
```json
{
  "success": true,
  "prompt": "Find tenders for bridge construction in Chattogram district",
  "agent_id": "agent-001-tender-radar",
  "agent_name": "Tender Radar Agent",
  "language": "en",
  "ollama_available": true,
  "result": {
    "status": "success",
    "output": {
      "tenders_found": 12,
      "filters": {"district": "Chattogram", "nature": "bridge"},
      "summary": "Found 12 tenders matching bridge construction in Chattogram"
    }
  },
  "interpretation": {
    "determined_agent": "agent-001-tender-radar",
    "alternative_agents": ["agent-038-tender-pre-screener"],
    "reasoning": "Prompt matches tender radar capabilities"
  }
}
```

---

## Error Codes

| Code | HTTP | Scenario |
|------|------|----------|
| `AGENT_NOT_FOUND` | 404 | Agent ID not registered |
| `AGENT_NOT_READY` | 409 | Agent in maintenance/unavailable |
| `AGENT_TIMEOUT` | 408 | Agent execution exceeded timeout |
| `AGENT_EXECUTION_FAILED` | 500 | Agent failed unexpectedly |
| `CELERY_UNAVAILABLE` | 503 | Redis/Celery broker unavailable |
| `OLLAMA_NOT_AVAILABLE` | 503 | Ollama inference service not running |

---

## Permission Requirements

| Endpoint | Required Role | Notes |
|----------|---------------|-------|
| All (except `/repo/facts`) | `viewer` or higher | Tenant-scoped agent results |
| `/agents/whatsapp-automation/*` | `estimator` or `admin` | WhatsApp credentials required |
| Long-running agents | `editor` or higher | Access to background processing |

> **Long-running agents**: `agent-025-knowledge-lake`, `agent-026-learning`, `agent-027-orchestrator`, `agent-048-material-price-crawler`

---

## Rate Limits

| Endpoint | Limit | Window |
|----------|-------|--------|
| `/agents` | 60 | 60 |
| `/agents/{agent_id}` | 60 | 60 |
| `/agent-results/recent` | 120 | 60 |
| `/agents/{agent_id}/run` | 30 | 60 |
| `/agents/whatsapp-automation/*` | 10 | 60 |
| `/agents/ollama-run` | 30 | 60 |

---

## Caching

- `GET /agents/*`: `public, max-age=300` (agent metadata rarely changes)
- `GET /agent-results/recent`: `private, max-age=60` (recent execution results)
- Other: `no-store` (writes) or `private, max-age=30`

---

## React Query Mapping

```typescript
export const agentKeys = {
  all: ['agents'] as const,
  byId: (agentId: string) => [...agentKeys.all, 'detail', agentId] as const,
  results: (limit: number) => [...agentKeys.all, 'results', { limit }] as const,
  run: (agentId: string) => [...agentKeys.all, 'run', agentId] as const,
  whatsapp: () => [...agentKeys.all, 'whatsapp'] as const,
  ollama: () => [...agentKeys.all, 'ollama'] as const,
};

export function useAgent(agentId: string) {
  return useQuery({
    queryKey: agentKeys.byId(agentId),
    queryFn: () => apiFetch<AgentDetails>(`/agents/${agentId}`),
    staleTime: 300_000,
  });
}

export function useAgentRun(agentId: string) {
  return useMutation({
    mutationFn: (context: AgentContext) => apiFetch<AgentRunResult>(`/agents/${agentId}/run`, {
      method: 'POST',
      body: JSON.stringify(context),
    }),
    onSuccess: (data) => {
      if (data.async) {
        // Start polling for result
        queryClient.invalidateQueries({ queryKey: agentKeys.byId(agentId) });
      }
    },
  });
}
```

---

## Zustand Store

```typescript
// stores/agents.ts
interface AgentState {
  agents: Record<string, AgentDetails>;\n  recentResults: AgentResult[];\n  systemStatus: SystemStatus | null;\n  \n  loadAgents: () => Promise<void>;\n  getAgent: (id: string) => AgentDetails | null;\n  runAgent: (id: string, context: AgentContext) => Promise<AgentRunResult>;\n  setRecentResults: (results: AgentResult[]) => void;\n}
```

---

## Pipeline Integration

**Orchestrator Endpoints**:
- `/api/pipeline/phases` - List phases and agents
- `/api/pipeline/run-async` - Run pipeline in background
- `/api/pipeline/status/{task_id}` - Poll Celery task status

**Pipeline Phases**:
1. **Discovery** (Agent-001 to Agent-003)
2. **Qualification** (Agent-004 to Agent-010)
3. **Tender Processing** (Agent-012 to Agent-017)
4. **Pricing** (Agent-011, Agent-012, Agent-015)
5. **Compliance** (Agent-007, Agent-009, Agent-037)
6. **Intelligence** (Agent-013 to Agent-019)
7. **Competitor Analysis** (Agent-013 to Agent-017)
8. **Learning** (Agent-026)

---

## Versioning

- `v1`: Current (Agent metadata, execution, orchestration)
- `v2` (planned): GraphQL queries, agent composition builder

---

## Monitoring & Telemetry

**Metrics per Agent**:
- Success/failure rate
- Average execution time
- Memory usage
- API calls made
- User-agent interactions

**Agent Health**:
- Process status (running/idle/failed)
- Resource utilization
- Dependency health checks
- Retry attempts and backoff

**Alerting**:
- Agent failures > 5% of total
- Processing time > 2x threshold
- Dependency unavailability

> **Integration**: `/app/agents/runner.py` orchestrates agent execution, `/app/agents/registry.py` maintains agent metadata and lifecycle

---

## Security Considerations

**Agent Isolation**:
- Each agent runs in separate sandbox context
- Tenant-scoped access controls
- Resource limits per agent execution

**Credential Management**:
- OAuth tokens for external APIs (e-GP, WhatsApp)
- Redis-backed secure storage for API keys
- Automated credential rotation

**Audit Logging**:
- All agent executions logged with context
- Success/failure metrics tracked
- Suspicious patterns flagged for review

---

## OpenAPI Reference

See `/openapi.json#/paths/~1api~1agents~1{agent_id}~1run/post`