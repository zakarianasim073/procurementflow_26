# ProcureFlow BD — Architecture Decision Records (ADRs)

## ADR-001: Multi-Agent Architecture with Central Brain

**Status**: Accepted  
**Date**: 2024-06-15  
**Deciders**: Architecture Team

### Context
ProcureFlow needs to coordinate 49+ specialized AI agents for procurement intelligence. Agents need to:
- Communicate with each other
- Share knowledge
- Execute in workflows
- Be discoverable

### Decision
Implement a central **Agent Brain** (`app/agents/core/brain.py`) as the nervous system:
- Agent Registry: Knows all agents and capabilities
- Message Bus: Async pub/sub via in-memory queue + Redis Streams
- Knowledge Store: Shared facts (in-memory LRU + PostgreSQL persisted)
- Query Router: Routes questions to capable agents
- Workflow Orchestrator: Chains agent executions

### Consequences
- ✅ Loose coupling between agents
- ✅ Horizontal scaling via Redis Streams
- ✅ Single source of truth for knowledge
- ⚠️ Brain is single point of failure (mitigated by Redis clustering)
- ⚠️ In-memory knowledge store not shared across replicas (mitigation: pgvector)

---

## ADR-002: Dual ORM Layer — Legacy + Canonical Models

**Status**: Superseded (Migration in progress)  
**Date**: 2024-01-10  
**Deciders**: Backend Team

### Context
Two SQLAlchemy bases exist:
- `app.db.models.Base` — Legacy, 60+ tables
- `app.models.Base` — Canonical, modern, typed

### Decision
**Migrate fully to `app.models`** (canonical):
- Delete `app.db.models.Tender` (conflicts with `app.models.tender.Tender`)
- Unify Alembic to track single metadata
- Complete `intelligence_data_service.py` → domain services extraction

### Consequences
- ✅ Single source of truth
- ✅ Type-safe models with Mapped[]
- ⚠️ Migration effort: ~2 weeks
- ⚠️ ETL scripts need updates

---

## ADR-003: SOR Rate Matching — Multi-Agency with Zone Support

**Status**: Accepted  
**Date**: 2024-03-01  
**Deciders**: Domain Experts, Backend Team

### Context
Bangladesh has 3 SOR agencies with different code formats:
- BWDB: `XX-XXX-XX` (1024 rates)
- PWD: `XX.XX...` (2018 rates)  
- LGED: `X.XX.XX...` (1503 rates)
Plus 4 zones (A/B/C/D) with different agency mappings

### Decision
Single `SORService` (`app/sor/sor_service.py`) with:
- Agency detection via suffix `(PWD)/(LGED)/(BWDB)` → pattern fallback
- Zone resolution via Division → Agency Zone mapping table
- Prefix matching for group codes
- Description-based fuzzy matching (SequenceMatcher) as last resort
- Load from PostgreSQL (preferred) or CSV fallback

### Consequences
- ✅ Zero-ambiguity agency detection
- ✅ Handles legacy code formats
- ⚠️ Description matching threshold (0.42) needs tuning
- ⚠️ No batch lookup — N×3 queries per BOQ item (optimization planned)

---

## ADR-004: BOQ Comparison — Async Offload to Celery

**Status**: Accepted (Implementation pending)  
**Date**: 2024-05-15  
**Deciders**: Architecture Team

### Context
Current `/api/boq/compare` does parsing, SOR matching, Excel/DOCX generation synchronously (30-60s).

### Decision
Offload to Celery worker:
1. API accepts upload → returns `job_id`
2. Celery task runs comparison
3. Status polling endpoint `/api/boq/status/{job_id}`
4. Result download endpoint when complete

### Consequences
- ✅ Non-blocking API
- ✅ Progress tracking
- ✅ Horizontal worker scaling
- ⚠️ Requires Redis + Celery infrastructure
- ⚠️ File storage for generated reports (MinIO)

---

## ADR-005: PostgreSQL as Primary Store — No JSON Cache

**Status**: Accepted  
**Date**: 2024-02-01  
**Deciders**: Architecture Team

### Context
Previous version used in-memory `SESSION_CACHE` dict + JSON files.

### Decision
All persistent data in PostgreSQL 17:
- Core tables: tenders, awards, app_records, lifecycle
- Intelligence: knowledge_entries, agent_results, contractor_dna
- Pre-computed: npp_records, pre_computed_intelligence
- SOR: sor_rates (3 agencies × 4 zones)

### Consequences
- ✅ Durability, ACID, queryability
- ✅ Multi-tenant RLS support
- ⚠️ Migration management via Alembic
- ⚠️ Connection pooling critical (60 max)

---

## ADR-006: Works-Only Filtering at Scan Stage

**Status**: Accepted  
**Date**: 2024-04-01  
**Deciders**: Product, Domain Experts

### Context
e-GP has Goods, Works, Services, Supply categories. ProcureFlow focuses on civil construction.

### Decision
Filter `category == "Works"` at Tender Radar scan (`tender_radar.py:_scan_all()`). All downstream agents assume Works context.

### Consequences
- ✅ Reduced data volume (~60% filter)
- ✅ Domain-specific agents (SOR, PPR 2025)
- ⚠️ Cannot expand to Goods/Services without architecture changes

---

## ADR-007: JWT Authentication with Tenant Context

**Status**: Accepted  
**Date**: 2024-03-15  
**Deciders**: Security Team

### Context
Multi-tenant SaaS needs authentication + authorization.

### Decision
- HS256 JWT with `tenant_id`, `role`, `scopes` claims
- Middleware validates on all `/api` routes (except public prefixes)
- RLS policies enforce tenant isolation at DB level
- `REQUIRE_API_AUTH` env var (default true) — **must not be disabled in prod**

### Consequences
- ✅ Stateless auth
- ✅ Row-level security
- ⚠️ JWT secret auto-generated to `.jwt_secret` file — **must use env var in prod**
- ⚠️ No token rotation (short expiry 24h mitigates)

---

## ADR-008: e-GP Crawling — Subprocess Isolation

**Status**: Accepted  
**Date**: 2024-05-01  
**Deciders**: Backend Team

### Context
e-GP portal has connection issues (WinError 10060) in long-running processes.

### Decision
Crawler runs as separate subprocess (`_sub_dl.py`):
- Clean Python process per crawl job
- Bypasses in-process socket exhaustion
- Communicates via JSON stdout

### Consequences
- ✅ Stable crawling
- ✅ Isolated failures
- ⚠️ Process overhead
- ⚠️ Shared session cookies via file

---

## ADR-009: Document Processing — pdfplumber + OCR Fallback

**Status**: Accepted  
**Date**: 2024-04-15  
**Deciders**: ML Team

### Context
Tender documents are PDFs (BOQ, TDS, NIT, Drawings). Need structured extraction.

### Decision
- Primary: `pdfplumber` table extraction
- Fallback: PyPDF2 text + regex parsing
- OCR: Tesseract for scanned PDFs (Bangla + English)
- Vision LLM: GPT-4o / Claude for complex layouts

### Consequences
- ✅ Handles multi-column BOQ tables
- ✅ Graceful degradation
- ⚠️ OCR accuracy varies
- ⚠️ Vision LLM adds latency/cost

---

## ADR-010: Async Implementation — FastAPI + SQLAlchemy Async

**Status**: Accepted  
**Date**: 2024-01-01  
**Deciders**: Backend Team

### Context
High-concurrency API with DB + external calls (LLM, e-GP).

### Decision
- FastAPI native async
- SQLAlchemy 2.0 async (`AsyncSession`, `asyncpg`)
- Celery for background tasks
- Redis Streams for agent message bus
- `asyncio.Queue` for in-process brain queue

### Consequences
- ✅ High throughput
- ✅ Proper backpressure
- ⚠️ Sync libraries need `run_in_executor`
- ⚠️ No blocking calls in async paths

---

## ADR-011: Configuration — Pydantic Settings + .env

**Status**: Accepted  
**Date**: 2024-02-15  
**Deciders**: DevOps Team

### Context
Multiple environments (dev, staging, prod) with secrets.

### Decision
- `pydantic-settings` BaseSettings
- Single `.env` at project root
- `.env.example` committed
- `.env` gitignored
- Environment-specific overrides: `.env.windows`, `.env.production`

### Consequences
- ✅ Type-safe config
- ✅ Validation on startup
- ⚠️ Multiple `.env` files loaded (precedence confusion)
- ⚠️ `DATABASE_URL` defaults to empty — **must validate required in prod**

---

## ADR-012: Observability — OpenTelemetry + Prometheus

**Status**: Partially Implemented  
**Date**: 2024-06-01  
**Deciders**: Platform Team

### Context
Need distributed tracing, metrics, logging.

### Decision
- OpenTelemetry SDK (optional, feature-flagged)
- Export to Tempo (traces) + Prometheus (metrics)
- Structured JSON logging with `request_id` correlation
- Health endpoints: `/api/health`, `/api/health/db`, `/api/health/agents`

### Consequences
- ✅ Vendor-neutral instrumentation
- ✅ Correlation across services
- ⚠️ OTel disabled by default — **must enable in prod**
- ⚠️ No Grafana dashboards yet

---

## ADR-013: Docker Deployment — Compose for Dev, K8s for Prod

**Status**: Accepted
**Date**: 2024-03-01
**Deciders**: DevOps Team

### Context
Containerized deployment needed. PostgreSQL must avoid collision with any host-side PG instance.

### Decision
- `docker-compose.yml` for local dev (Postgres, Redis, MinIO, API, Workers, Frontend)
- Multi-stage Dockerfile for production (planned)
- K8s manifests for production (planned)
- **Container-internal PG port is 5432** (all services connect via `postgres:5432`)
- **Host PG port is mapped to 5433** (`5433:5432`) to avoid collision with local PG
- PgBouncer on port 6432 (container + host, transaction mode)
- All DATABASE_URL references use container port 5432; host-side tools use 5433

### Consequences
- ✅ Consistent dev environment with no port collisions
- ✅ Clear distinction between container-internal and host-exposed ports
- ✅ PgBouncer protects PostgreSQL from connection exhaustion
- ⚠️ Host port 5433 must not conflict with other PG instances on dev machines

---

## ADR-014: Knowledge Graph — In-Memory NetworkX (Temporary)

**Status**: Superseded  
**Date**: 2024-05-01  
**Deciders**: ML Team

### Context
Need entity relationships (tenders, contractors, agencies).

### Decision
Current: `networkx` in-memory graph (lost on restart).  
**Target**: PostgreSQL adjacency list + `pgvector` for embeddings.

### Consequences
- ✅ Quick prototype
- ❌ Not production-ready
- 🔄 Migration to persistent graph planned

---

## ADR-015: ML Pipeline — On-Demand Training (Current) → Model Registry (Target)

**Status**: In Progress  
**Date**: 2024-06-01  
**Deciders**: ML Team

### Context
PPR 2025 SLT/NPPI models, Win Probability, Competitor Price Predictor.

### Decision
Current: Train on-demand in API request (30s+ latency).  
Target: Pre-train via Celery Beat → Model Registry (MLflow) → Serve cached.

### Consequences
- ✅ Fresh models
- ❌ Unacceptable latency
- 🔄 Migration to model serving architecture

---

## ADR-016: Package Number as Universal Join Key

**Status**: Accepted  
**Date**: 2024-04-15  
**Deciders**: Data Team

### Context
Linking APP → Tender → Award → eExperience across sources.

### Decision
`package_no` + `work_name` as primary join keys across all tables. Normalization via `normalize_package()` (uppercase, remove spaces/special chars, preserve alphanumeric+/./_-).

### Consequences
- ✅ Cross-source linkage
- ✅ Handles format variations
- ⚠️ Fuzzy matching needed for OCR errors
- ⚠️ Some APP records lack tender_id

---

## ADR-017: Agent Result Persistence — Shared Session Pattern

**Status**: Accepted  
**Date**: 2024-05-15  
**Deciders**: Backend Team

### Context
Agents persist results. Creating new session per agent = N+1 connections.

### Decision
Orchestrator creates single session → passes to agents via `store_result(result, session=shared)`. Agents use injected session if provided, else create own.

### Consequences
- ✅ Single transaction per pipeline
- ✅ Connection pool efficiency
- ⚠️ Requires orchestrator coordination
- ⚠️ Error handling complexity

---

## ADR-018: Tender Acquisition Agent — Two-Phase Download

**Status**: Accepted  
**Date**: 2024-05-20  
**Deciders**: Crawler Team

### Context
e-GP documents need reliable download.

### Decision
1. **Notice PDF**: `/GeneratePdf?reqURL=...` 
2. **All Documents ZIP**: `/TenderSecUploadServlet?funName=zipdownload` (most reliable)
3. **Individual Sections**: Scrape `TenderDocView.jsp` for Section 1-11
4. Extract BOQ/TDS text via pdfplumber → share via Brain

### Consequences
- ✅ Bulk download via ZIP avoids 0-byte individual downloads
- ✅ Text extraction enables Brain queries
- ⚠️ Demo account limitations (no BOQ/TDS via individual)
- ⚠️ Login flow requires JSESSIONID seeding

---

## ADR-019: PPR 2025 Compliance — Rules Engine as Config

**Status**: Accepted  
**Date**: 2024-06-01  
**Deciders**: Legal, Domain Experts

### Context
PPR 2025 effective Sep 28, 2025. SLT/ALT detection, NPPI calculation, Schedule 4/5/6 evaluation.

### Decision
Ruleset model (`app/db/models.py:Ruleset`) — versioned JSON rules. Engine evaluates against tender data. Not hardcoded.

### Consequences
- ✅ Adapt to regulation changes
- ✅ Audit trail of rule versions
- ⚠️ Rules DSL complexity
- ⚠️ Testing matrix grows

---

## ADR-020: Multi-Tenant RLS — Row-Level Security at DB

**Status**: Accepted (Migration 011)  
**Date**: 2024-06-15  
**Deciders**: Security, Architecture

### Context
SaaS with data isolation per tenant.

### Decision
PostgreSQL RLS policies on all tenant-scoped tables. Middleware sets `app.current_tenant_id` per request. Read-replica must also set context.

### Consequences
- ✅ Database-enforced isolation
- ✅ No application-layer bugs leak data
- ⚠️ Read-replica context gap — **must fix**
- ⚠️ Superuser bypasses RLS (admin only)

---

---

## ADR Index

| ADR | Title | Status | Priority |
|-----|-------|--------|----------|
| 001 | Multi-Agent Architecture with Central Brain | Accepted | Core |
| 002 | Dual ORM Layer — Migration to Canonical | Superseded | P0 |
| 003 | SOR Rate Matching — Multi-Agency + Zones | Accepted | Core |
| 004 | BOQ Comparison — Async Celery Offload | Accepted | P0 |
| 005 | PostgreSQL Primary Store | Accepted | Core |
| 006 | Works-Only Filtering | Accepted | Domain |
| 007 | JWT Auth + Tenant Context | Accepted | Security |
| 008 | e-GP Crawling — Subprocess Isolation | Accepted | Reliability |
| 009 | Document Processing — pdfplumber + OCR | Accepted | ML |
| 010 | Async FastAPI + SQLAlchemy | Accepted | Core |
| 011 | Pydantic Settings Config | Accepted | DevOps |
| 012 | Observability — OTel + Prometheus | Partial | P1 |
| 013 | Docker Compose + K8s | Accepted | DevOps |
| 014 | Knowledge Graph — Persistent Migration | Superseded | P1 |
| 015 | ML Pipeline — Model Registry | In Progress | P1 |
| 016 | Package No Universal Join Key | Accepted | Data |
| 017 | Agent Result Shared Session | Accepted | Performance |
| 018 | Tender Acquisition Two-Phase | Accepted | Crawler |
| 019 | PPR 2025 Rules Engine | Accepted | Domain |
| 020 | Multi-Tenant RLS | Accepted | Security |