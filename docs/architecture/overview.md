# ProcureFlow BD — System Architecture Overview

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           PROCUREFLOW ENTERPRISE SYSTEM                      │
└─────────────────────────────────────────────────────────────────────────────┘

┌──────────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   FRONTEND   │────▶│   API GATEWAY │────▶│  AGENT BRAIN  │────▶│  KNOWLEDGE   │
│  (Next.js 14)│     │  (FastAPI)    │     │  (Orchestrator)│     │   LAKE       │
└──────────────┘     └──────┬───────┘     └──────┬───────┘     └──────┬───────┘
                            │                    │                    │
              ┌─────────────┼─────────────┐      │                    │
              ▼             ▼             ▼      ▼                    ▼
         ┌─────────┐  ┌───────────┐ ┌──────────┐ ┌──────────┐ ┌────────────┐
         │PostgreSQL│  │   Redis   │ │  MinIO   │ │ Celery   │ │  External  │
         │  (DB)    │  │ (Streams/  │ │ (Files)  │ │ Workers  │ │   APIs     │
         │          │  │  Cache)   │ │          │ │          │ │  (e-GP,    │
         └─────────┘  └───────────┘ └──────────┘ └──────────┘ └────────────┘
                            │
                            ▼
                     ┌──────────────┐
                     │  MONITORING  │
                     │ (OTel/Prom/  │
                     │  Grafana)    │
                     └──────────────┘
```

---

## Core Components

### 1. API Gateway (FastAPI)
**Location**: `backend/app/main.py`

**Responsibilities**:
- Request routing (core + deferred router loading)
- Authentication/Authorization middleware
- Audit logging on mutating requests
- CORS, security headers
- SPA static file serving
- Health checks

**Key Design Decisions**:
- Deferred router loading: Core routers at startup, 30+ deferred via background task
- Dual prefix: `/api` and `/api/v1` for all routes
- Request ID propagation via middleware

### 2. Agent Brain
**Location**: `backend/app/agents/core/brain.py`

**Responsibilities**:
- **Agent Registry**: 49 agents registered with capabilities
- **Message Bus**: In-memory `asyncio.Queue` + Redis Streams for cross-process
- **Knowledge Store**: LRU cache (2000 entries) + PostgreSQL persistence
- **Query Router**: Routes to agents by `can_query` capability
- **Workflow Engine**: DAG execution with dependency resolution
- **Idle Cycle**: Pre-emptive intelligence (5/15/30/60 min intervals)

**Agent Categories** (49 total):
| Category | Agents | Purpose |
|----------|--------|---------|
| Discovery | 4 | Tender radar, acquisition, watchdog |
| Document AI | 3 | Extraction, preparation, pre-screening |
| BOQ/Technical | 4 | BOQ intelligence, spec, eligibility, risk |
| Pricing/Rate | 5 | Rate analysis, market intel, SOR zone, fill, VAT |
| Competition | 4 | Competitor intel, award intel, pricing predictor, syndicate |
| Decision | 6 | PPR eval, LERT, win prob, bid optimizer, bid/no-bid, exec decision |
| Knowledge | 3 | Knowledge lake, company brain, market brain |
| Learning | 2 | Learning agent, vision intelligence |
| Utility | 10 | Resource, financial, RABill, WhatsApp, report gen, compliance, etc. |
| Client/Portal | 7 | Dashboard, PPR2025, APP forecast, client intel, etc. |

### 3. SOR Service
**Location**: `backend/app/sor/sor_service.py`

**Responsibilities**:
- Load rates from PostgreSQL (preferred) or CSV
- Agency detection (BWDB/PWD/LGED) via code patterns
- Zone resolution (A/B/C/D) via division mapping
- Rate lookup: exact → prefix → suffix → fuzzy description
- Description token matching (SequenceMatcher, threshold 0.42)

**Data**: ~4,545 rates across 3 agencies × 4 zones

### 4. BOQ Processor
**Location**: `backend/app/services/boq_processor.py` (inferred)

**Responsibilities**:
- Parse BOQ PDFs (pdfplumber tables → text fallback)
- Detect work type from BOQ items
- Match each item to SOR rates (3 agencies)
- Generate comparison results with flags (match/variance/mismatch)
- Export Excel + DOCX reports

**Current Limitation**: Synchronous in API request (ADR-004 addresses this)

### 5. Tender Acquisition Agent
**Location**: `backend/app/agents/acquisition/tender_acquisition.py`

**Responsibilities**:
- Login to e-GP (JSESSIONID seeding)
- Download Notice PDF, All Documents ZIP, Individual sections
- Extract BOQ/TDS text via pdfplumber
- Share knowledge via Agent Brain (`boq_text`, `tds_text` entries)

**Reliability**: Subprocess isolation (`_sub_dl.py`) to avoid WinError 10060

### 6. Intelligence Data Service (Monolith → Domain Services)
**Location**: `backend/app/services/intelligence_data_service.py` (4,500+ lines)

**Current State**: Monolith being split into domain services:
- `TenderMatchingService` — lifecycle, APP/Tender/Award matching
- `ContractorIntelligenceService` — DNA, win rates, pricing
- `MarketIntelligenceService` — SLT, NPPI, Moat analysis
- `ReportGenerationService` — executive reports
- `CrawlImportService` — JSON → DB import
- `DataQualityService` — validation, repair

### 7. Database Layer
**Location**: `backend/app/db/` + `backend/app/models/`

**Dual ORM Issue** (ADR-002):
- `app.db.models` — Legacy (60+ tables), used by ETL/crawlers
- `app.models` — Canonical (modern, typed), used by API/agents

**Core Tables**:
| Table | Purpose | Rows (est.) |
|-------|---------|-------------|
| `tenders` | Core tender records | 280K+ |
| `awards` | Contract awards | 150K+ |
| `app_records` | Annual Procurement Plans | 80K+ |
| `lifecycle` | APP↔Tender↔Award matching | 100K+ |
| `knowledge_entries` | Agent shared intelligence | 2K+ |
| `agent_results` | Agent execution history | 50K+ |
| `sor_rates` | Schedule of Rates | 4,545 |
| `contractor_dna` | Contractor profiles | 30K+ |

### 8. Background Workers (Celery)
**Location**: `backend/app/workers/`

**Queues** (planned: priority separation):
- `default` — All tasks currently
- `high` — Tender radar, alerts (planned)
- `low` — Report generation, ML training (planned)

**Task Categories**:
| Module | Tasks |
|--------|-------|
| `agent_tasks` | Agent pipeline execution |
| `boq_tasks` | BOQ comparison, report gen |
| `document_tasks` | PDF processing, OCR |
| `pipeline_tasks` | Multi-agent workflows |
| `notification_tasks` | Email, webhook delivery |
| `report_tasks` | Scheduled reports |

---

## Data Flow Patterns

### 1. BOQ Comparison Flow (Current)
```
POST /api/boq/compare (file) 
    → parse BOQ PDF (pdfplumber)
    → detect work_type per item
    → for each item: SOR lookup × 3 agencies
    → compute diffs, flags
    → generate Excel + DOCX
    → persist BOQComparison + BOQItems
    → return results + file paths
```
**Latency**: 30-60s (blocks worker)

### 2. BOQ Comparison Flow (Target — ADR-004)
```
POST /api/boq/compare (file)
    → save file to MinIO
    → enqueue Celery task
    → return {job_id, status_url}

Celery Worker:
    → parse, match, generate reports
    → upload to MinIO
    → update job status

GET /api/boq/status/{job_id}
    → poll until complete

GET /api/boq/result/{job_id}
    → download URLs
```

### 3. Tender Acquisition Flow
```
Cron / Manual Trigger
    → TenderAcquisitionAgent.execute()
    → Login e-GP (JSESSIONID)
    → SearchNoaServlet (keywords) / TenderDetailsServlet (pages)
    → For each tender:
        → Download Notice PDF
        → Download All Docs ZIP
        → Extract BOQ/TDS text
        → brain.store_knowledge("boq_text", tender_id, ...)
        → brain.store_knowledge("tds_text", tender_id, ...)
    → Save files to uploads/{tender_id}/
```

### 4. Agent Pipeline Flow
```
WorkflowOrchestrator.run_workflow([
    {"agent_id": "tender-radar", "input": {...}},
    {"agent_id": "tender-acquisition", "depends_on": ["tender-radar"]},
    {"agent_id": "boq-intelligence", "depends_on": ["tender-acquisition"]},
    {"agent_id": "rate-analysis", "depends_on": ["boq-intelligence"]},
    {"agent_id": "competitor-intelligence", "depends_on": ["award-intelligence"]},
    {"agent_id": "win-probability", "depends_on": ["rate-analysis", "competitor-intelligence"]},
    {"agent_id": "executive-decision", "depends_on": ["win-probability", "bid-optimizer"]}
])
    → Brain executes in dependency order
    → Each agent stores result to DB (shared session)
    → Results passed to downstream agents via context
```

### 5. Knowledge Sharing Flow
```
Agent executes → discovers insight
    → brain.store_knowledge(
        agent_id="rate-analysis",
        entry_type="sor_match",
        tender_id="123456",
        data={...},
        summary="Item 40-300-10 matched to BWDB Zone C at 1,250 BDT",
        tags=["bwdb", "zone-c", "match"]
    )
    → Persisted to knowledge_entries table
    → Embedded in project_memory (vector search)
    → Available to all agents via brain.query_knowledge()
```

---

## Technology Stack

| Layer | Technology | Version | Purpose |
|-------|------------|---------|---------|
| **API** | FastAPI | 0.115+ | Async web framework |
| **Async DB** | SQLAlchemy + asyncpg | 2.0 / 24.06 | PostgreSQL async ORM |
| **DB** | PostgreSQL | 17 | Primary data store |
| **Queue** | Redis + Celery | 7.x / 5.4 | Task queue, streams |
| **Cache** | Redis | 7.x | Session, rate limit, cache |
| **Files** | MinIO | Latest | S3-compatible object storage |
| **AI Primary** | Anthropic Claude | Sonnet 4 | Structured extraction, reasoning |
| **AI Fallback** | OpenAI | GPT-4o | Backup LLM |
| **Local LLM** | Ollama | qwen2.5:7b | Offline/private inference |
| **OCR** | Tesseract + pdfplumber | 5.x / 0.11 | PDF text/table extraction |
| **Vector** | pgvector / project_memory | 0.7+ | Embeddings, semantic search |
| **Auth** | JWT (HS256) | — | Stateless auth + tenant context |
| **Monitoring** | OpenTelemetry + Prometheus | 1.x | Traces, metrics |
| **Frontend** | Next.js 14 + Tailwind | 14.x | React SPA |
| **Container** | Docker Compose / K8s | — | Deployment |

---

## Key Design Patterns

| Pattern | Usage |
|---------|-------|
| **Registry** | Agent registration in Brain (`register_all_agents`) |
| **Message Bus** | AgentBrain `_message_queue` + Redis Streams |
| **Knowledge Lake** | Central `knowledge_entries` table + vector index |
| **Workflow/DAG** | `AgentBrain.run_workflow()` with dependency resolution |
| **Repository** | Service layer over SQLAlchemy (in progress) |
| **Factory** | `SORService.find_rate()` agency detection |
| **Strategy** | LLM provider selection (Claude/OpenAI/Ollama) |
| **Observer** | Webhook events on agent completion |
| **Circuit Breaker** | `runtime_guards.py` distributed locks |
| **Decorator** | `@brain.on_message(agent_id)` for handlers |

---

## Security Boundaries

```
┌────────────────────────────────────────────────────────────────┐
│                    EXTERNAL REQUESTS                            │
└──────────────────────────┬─────────────────────────────────────┘
                           ▼
┌────────────────────────────────────────────────────────────────┐
│  MIDDLEWARE: Auth + Tenant Context + Audit Log                 │
│  - JWT validation (HS256)                                       │
│  - RLS context: SET app.current_tenant_id = 'xxx'              │
│  - Audit log on POST/PUT/PATCH/DELETE                          │
└──────────────────────────┬─────────────────────────────────────┘
                           ▼
┌────────────────────────────────────────────────────────────────┐
│  ROUTER LAYER (FastAPI)                                        │
│  - require_scope / require_role dependencies                   │
│  - Pagination, validation, rate limiting                       │
└──────────────────────────┬─────────────────────────────────────┘
                           ▼
┌────────────────────────────────────────────────────────────────┐
│  SERVICE LAYER (Domain Services)                               │
│  - Business logic, DB transactions                             │
│  - Agent orchestration                                         │
└──────────────────────────┬─────────────────────────────────────┘
                           ▼
┌────────────────────────────────────────────────────────────────┐
│  DATA LAYER (PostgreSQL + RLS)                                 │
│  - Row-Level Security policies                                 │
│  - Tenant isolation enforced at DB level                       │
└────────────────────────────────────────────────────────────────┘
```

---

## Scalability Considerations

| Component | Current Limitation | Scaling Strategy |
| 
|-----------|-------------------|------------------|
| **Agent Brain** | In-memory `_knowledge_store`, single process | Redis-backed cache, stateless API replicas |
| **BOQ Comparison** | Sync in request (30-60s) | Celery offload, priority queues |
| **SOR Lookup** | N×3 queries per item | Batch `IN` query, pg_trgm index |
| **Knowledge Graph** | In-memory NetworkX | PostgreSQL adjacency + pgvector |
| **ML Inference** | On-demand training | Model registry, batched serving |
| **Database** | Single primary | Read replicas, connection pooling (60 max) |
| **File Storage** | Local/MinIO | MinIO cluster, CDN for reports |
| **Crawlers** | Sequential pages | Parallel with rate limiting |

---

## Deployment Architecture

### Development (Docker Compose)
```
services:
  postgres:  port 5433  (NOT 5432!)
  redis:     port 6379
  minio:     port 9000/9001
  api:       port 8000  → depends on postgres, redis, minio
  worker:    celery -A app.workers.celery_app
  frontend:  port 5173  → proxies to api
```

### Production (Kubernetes - Planned)
```
Namespace: procureflow
├── Ingress (TLS, rate limit)
├── API Deployment (HPA: CPU>70%, replicas 3-20)
├── Worker Deployment (HPA: queue depth, replicas 2-10)
│   ├── Priority: high (tender radar)
│   ├── Priority: default (BOQ, agents)
│   └── Priority: low (reports, ML)
├── PostgreSQL (Primary + 2 Replicas, Patroni)
├── Redis Cluster (3 masters + replicas)
├── MinIO Cluster (4 nodes)
├── Monitoring Stack (Prometheus, Grafana, Tempo, Loki)
└── Cert-Manager (Let's Encrypt)
```

---

## Related Documents

- [ADRs](./ADRs.md) — Architecture Decision Records
- [Component Documentation](./components.md) — Deep dive per component
- [Integration Workflows](./integration-workflows.md) — Cross-system flows
- [API Documentation](../api/README.md) — Endpoint specifications
- [Database Schema](../database/schema.md) — Table definitions
- [Onboarding Guide](../onboarding/README.md) — Developer setup