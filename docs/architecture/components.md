# ProcureFlow BD — Component Documentation

## Table of Contents
1. [API Gateway (FastAPI)](#api-gateway)
2. [Agent Brain](#agent-brain)
3. [SOR Service](#sor-service)
4. [BOQ Processor](#boq-processor)
5. [Tender Acquisition Agent](#tender-acquisition-agent)
6. [Intelligence Data Service](#intelligence-data-service)
7. [Database Layer](#database-layer)
8. [Background Workers (Celery)](#background-workers)
9. [Document Processing](#document-processing)
10. [Authentication & Authorization](#authentication--authorization)

---

## 1. API Gateway (FastAPI) {#api-gateway}

**Location**: `backend/app/main.py`  
**Lines**: 473  
**Entry Point**: `uvicorn app.main:app`

### Responsibilities
- Application lifecycle (lifespan context manager)
- Router registration (core + deferred)
- Authentication middleware
- Audit logging middleware
- Static file serving (SPA)
- Health endpoints

### Key Classes/Functions

#### `lifespan(app: FastAPI)` — Application Lifecycle
```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup:
    # 1. Ensure directories (uploads, outputs, data, tenders)
    # 2. Optional: init_db() if PROCUREFLOW_INIT_DB_ON_STARTUP=1
    # 3. Load SOR rates (prefer_db from env)
    # 4. Include core API routers (13 modules)
    # 5. Start deferred router loading (background task)
    # 6. Optional: start Agent Brain if PROCUREFLOW_START_AGENTS_ON_STARTUP=1
    # 7. Configure OpenTelemetry
    yield
    # Shutdown:
    # - Cancel agent runtime task
    # - Cancel API router task
    # - Stop Agent Brain
    # - Close DB connections
```

#### Middleware: `enterprise_request_context`
```python
@app.middleware("http")
async def enterprise_request_context(request: Request, call_next):
    # 1. Generate/extract request_id, trace_id
    # 2. Auth check on /api routes (except public prefixes)
    # 3. Execute request
    # 4. Add security headers (CSP, X-Frame-Options, etc.)
    # 5. Audit log mutating requests to DB (async session)
```

#### Router Loading Strategy
```python
# Core routers (loaded at startup, synchronous)
CORE_V1_ROUTER_MODULES = [
    "auth", "boq", "sor", "competitors", "pricing", "contractors",
    "search", "validation", "reports", "system", "monitoring",
]

# Deferred routers (loaded in background thread)
DEFERRED_V1_ROUTER_MODULES = [
    "tenders", "awards", "dashboard", "chat", "epw3", "escalation",
    "market_index", "intelligence", "ppr2025", "analytics", "deptree",
    "predictions", "executive", "agents", "communication", "tender_processing",
    "embeddings", "payments", "webhooks",
]
```

### Configuration
| Env Var | Default | Description |
|---------|---------|-------------|
| `PROCUREFLOW_HOST` | `0.0.0.0` | Bind address |
| `PROCUREFLOW_PORT` | `8000` | Port |
| `PROCUREFLOW_RELOAD` | `false` | Hot reload |
| `PROCUREFLOW_INIT_DB_ON_STARTUP` | `0` | Auto-migrate |
| `PROCUREFLOW_SOR_DB_ON_STARTUP` | `0` | Load SOR from DB |
| `PROCUREFLOW_START_AGENTS_ON_STARTUP` | `0` | Start Agent Brain |

### Health Endpoints
```
GET /api/health
Response: {
    "status": "healthy",
    "api_routers_loaded": true,
    "agent_runtime_ready": false,
    "api_routers_error": null,
    "agent_runtime_error": null
}
```

---

## 2. Agent Brain {#agent-brain}

**Location**: `backend/app/agents/core/brain.py`  
**Lines**: 971  
**Instance**: `app.state.brain` (singleton per process)

### Core Capabilities

#### Agent Registry
```python
def register_agent(self, agent_id: str, instance: Any, 
                   name: str = "", description: str = "",
                   input_types: List[str] = None,
                   output_types: List[str] = None,
                   can_query: List[str] = None,
                   version: str = "1.0.0") -> AgentCapability:
    # Registers agent with metadata
    # Auto-creates default message handler calling agent.run()
```

#### Message Bus
```python
# In-memory queue (per process)
self._message_queue: asyncio.Queue = asyncio.Queue()

# Redis Streams for cross-process (when connected)
self._event_bus_connected: bool = False

async def send_message(self, message: BrainMessage) -> bool:
    await self._persist_message(message)  # DB persistence
    await self._publish_message_event(message)  # Redis Streams
    await self._message_queue.put(message)  # Local queue
    return True
```

#### Knowledge Store
```python
# In-memory LRU cache (max 2000 entries)
self._knowledge_store: Dict[str, Dict[str, Any]] = {}

async def store_knowledge(self, agent_id: str, entry_type: str, 
                          tender_id: str, data: Dict,
                          summary: str = "", tags: List[str] = None) -> str:
    # 1. Persist to knowledge_entries table (raw SQL)
    # 2. Cache in _knowledge_store with LRU eviction
    # 3. Upsert to project_memory (vector index)
    return entry_id
```

#### Query Router
```python
async def query_knowledge(self, entry_type: str = None, 
                          tender_id: str = None, tags: List[str] = None,
                          limit: int = 100, search_text: str = "",
                          agent_id: str = None) -> List[Dict]:
    # 1. Try semantic search via project_memory
    # 2. Fallback to in-memory cache filter
    # 3. Fallback to DB query
```

#### Workflow Engine
```python
async def run_workflow(self, workflow: List[Dict], context: Dict = None):
    # workflow = [
    #   {"agent_id": "agent-001", "input": {...}, "depends_on": []},
    #   {"agent_id": "agent-002", "input": {...}, "depends_on": ["agent-001"]},
    # ]
    # Executes in dependency order, passes results via context
```

#### Idle Cycle (Background Intelligence)
```python
async def _idle_time_cycle(self):
    # 5 min: Quick tender check
    # 15 min: Pre-screener
    # 30 min: MOAT/SLT analysis
    # 60 min: Full intelligence refresh
    # Hardcoded agent IDs: agent-038, agent-036
```

### Agent Registration (main.py)
```python
def register_all_agents(registry, brain=None):
    agents = [
        TenderRadarAgent(brain=brain),
        TenderAcquisitionAgent(brain=brain),
        # ... 47 more agents
        WorkflowOrchestrator(brain=brain),
    ]
    registry.register_many(*agents)
```

---

## 3. SOR Service {#sor-service}

**Location**: `backend/app/sor/sor_service.py`  
**Lines**: 561  
**Instance**: `sor_service` (singleton)

### Data Model
```python
@dataclass
class SorRate:
    agency: str          # BWDB, PWD, LGED
    code: str            # Raw code (e.g., "40-300-10")
    description: str     # Item description
    unit: str            # Normalized unit (cum, sqm, no, etc.)
    zone_a: float        # Zone A rate (BDT)
    zone_b: float        # Zone B rate
    zone_c: float        # Zone C rate
    zone_d: float        # Zone D rate
    
    def get_rate(self, zone: Optional[str] = None) -> float:
        return {'A': self.zone_a, 'B': self.zone_b, 
                'C': self.zone_c, 'D': self.zone_d}.get(zone.upper(), self.zone_a)
```

### Agency Detection (Priority Order)
```python
# 1. Suffix in code: "(PWD)", "(LGED)", "(BWDB)"
if '(PWD)' in code.upper(): return 'PWD'

# 2. Pattern matching on cleaned code
BWDB:  ^\d{2}-\d{3}-\d{2}$       (e.g., 40-300-10)
PWD:   ^\d{2}\.\d+(\.\d+)*$      (e.g., 26.50.1, 12.1.1.1)
LGED:  ^[2-9]\.\d{2}(\.\d+)*$    (e.g., 4.09.01.01)

# 3. Special PWD formats
EM codes:    EM\d+\.\d+...
Dash codes:  02-1-2, 15-1-1 (legacy PWD)
Prefix:      PWD 03.1
```

### Zone Resolution
```python
# Division → Agency Zone mapping (SOR PDF p11)
# LGED swaps C↔D vs PWD/BWDB
zone_map = {
    "Dhaka": {"BWDB": "A", "PWD": "A", "LGED": "A"},
    "Chattogram": {"BWDB": "B", "PWD": "B", "LGED": "B"},
    "Khulna": {"BWDB": "C", "PWD": "C", "LGED": "D"},  # LGED swap!
    "Rajshahi": {"BWDB": "D", "PWD": "D", "LGED": "C"}, # LGED swap!
}
```

### Rate Lookup Algorithm
```python
def find_rate(self, code: str, description: str = '',
              agency: str = 'BWDB', zone: Optional[str] = None):
    # 1. Parse compound code "A&B" → use B
    # 2. Detect agency from suffix
    # 3. Exact match on normalized code
    # 4. Prefix match (group codes) — min 3 chars
    # 5. Suffix match (with agency suffix removed)
    # 6. Full compound code as-is
    # 7. Fuzzy description match (SequenceMatcher, threshold 0.42)
```

### Data Loading
```python
def load_all(self, prefer_db: bool = True):
    if prefer_db and self._load_from_db():
        return
    # Fallback to CSV files
    for agency in ['BWDB', 'PWD', 'LGED']:
        csv_path = BASE_DIR / agency.lower() / "rates.csv"
        self._load_csv(agency, csv_path)
```

---

## 4. BOQ Processor {#boq-processor}

**Location**: `backend/app/services/boq_processor.py` (inferred from API)  
**API**: `backend/app/api/v1/boq.py`

### Processing Pipeline
```python
async def compare_boq(file: UploadFile, sor_agency: str, zone: str, 
                       tender_info: dict = None):
    # 1. Save uploaded file
    # 2. Parse PDF → BOQ items (pdfplumber tables)
    # 3. Detect work_type per item (from description)
    # 4. For each item:
    #    - Extract code, description, unit, quantity, quoted_rate
    #    - Call sor_service.find_rate(code, description, sor_agency, zone)
    #    - Compute diff, pct_diff, flag
    # 5. Aggregate statistics
    # 6. Generate Excel report (openpyxl)
    # 7. Generate DOCX report (python-docx)
    # 8. Persist to DB (BOQComparison + BOQItems)
```

### BOQ Item Flags
| Flag | Meaning |
|------|---------|
| `match` | Exact SOR code match |
| `variance` | Rate differs from SOR |
| `mismatch` | No SOR match found |
| `below_sor` | Quoted rate < SOR rate |

### Brain Compare (Alternative)
```python
POST /api/boq/brain-compare
{
    "tender_id": "1298004",
    "sor_agency": "BWDB", 
    "zone": "A"
}
# Uses brain knowledge (boq_text, tds_text) instead of file upload
```

### Current Limitation
- **Synchronous execution** (30-60s)
- Blocks FastAPI worker
- **Fix**: ADR-004 → Celery offload

---

## 5. Tender Acquisition Agent {#tender-acquisition-agent}

**Location**: `backend/app/agents/acquisition/tender_acquisition.py`  
**Subprocess**: `backend/app/agents/acquisition/_sub_dl.py`

### Download Strategy
```python
async def acquire_tender(tender_id: str):
    # 1. Login e-GP (JSESSIONID seeding)
    #    GET / → POST /LoginSrBean?action=checkLogin → GET /Index.jsp
    
    # 2. Notice PDF
    #    GET /GeneratePdf?reqURL=http://www.eprocure.gov.bd/
    #    resources/common/ViewTender.jsp&reqQuery=id={tender_id}
    
    # 3. All Documents ZIP (most reliable)
    #    GET /TenderSecUploadServlet?
    #    tenderId={tender_id}&folderArchId=1&lotNo=Package&funName=zipdownload
    
    # 4. Individual Sections (TenderDocView.jsp scrape)
    #    GET /tenderer/TenderDocView.jsp?tenderId={tender_id}
    #    Parse HTML for Section 1-11 download links
    
    # 5. Extract text from BOQ/TDS PDFs
    #    pdfplumber → share via brain.store_knowledge("boq_text", ...)
    #    pdfplumber → share via brain.store_knowledge("tds_text", ...)
```

### Subprocess Isolation
```python
# _sub_dl.py runs as separate Python process
# Avoids WinError 10060 (socket exhaustion in long-running process)
# Communicates via JSON stdout
```

### File Storage
```
uploads/{tender_id}/
├── notice.pdf
├── documents.zip (extracted)
├── Section1_Instructions to Tenderer.pdf
├── Section2_Tender Data Sheet.pdf
├── Section3_General Conditions of Contract.pdf
├── Section4_Particular Conditions of Contract.pdf
├── Section5_Tender and Contract Forms.pdf + .docx
├── Section6_Bill of Quantities.pdf
├── Section7_General Specifications.pdf
├── Section8_Particular Specifications.docx
├── Section9_ES Specifications.pdf
├── Section10_Drawings.pdf
└── Section11_Appendix to the Tender.pdf
```

---

## 6. Intelligence Data Service {#intelligence-data-service}

**Location**: `backend/app/services/intelligence_data_service.py`  
**Lines**: 4,500+ (monolith being split)

### Current Monolith Structure
```python
class IntelligenceDataService:
    # 40+ methods including:
    - import_existing_json_data()        # Crawl JSON → DB
    - import_crawled_tender_data()       # Tender JSON → tenders table
    - import_crawled_award_data()        # Award JSON → awards table  
    - import_crawled_app_data()          # APP JSON → app_records table
    - reconcile_awards_to_app_records()  # Lifecycle matching
    - rebuild_contractor_intelligence()  # DNA computation
    - query_works_records()              # Dashboard queries
    - get_tender_radar()                 # Live tender feed
    - get_slt_analysis()                 # SLT/ALT detection
    - get_nppi_trends()                  # NPPI trends
    - get_competitor_map()               # Competitor intelligence
    # ... 30+ more methods
```

### Domain Service Extraction (In Progress)
| New Service | Responsibility | Status |
|-------------|----------------|--------|
| `TenderMatchingService` | APP↔Tender↔Award lifecycle | ✅ Done |
| `ContractorIntelligenceService` | Contractor DNA, win rates | ✅ Done |
| `MarketIntelligenceService` | SLT, NPPI, Moat analysis | 🔄 In Progress |
| `ReportGenerationService` | Executive reports | 🔄 In Progress |
| `CrawlImportService` | JSON → DB import | 🔄 In Progress |
| `DataQualityService` | Validation, repair | 🔄 In Progress |

### Key Methods (Facade Pattern)
```python
# Delegates to extracted services
async def reconcile_awards_to_app_records(self, progress=None):
    return await self._tender_matching.reconcile_awards_to_app_records(progress)

async def rebuild_contractor_intelligence(self):
    return await self._contractor_intelligence.rebuild_contractor_intelligence()
```

---

## 7. Database Layer {#database-layer}

### Dual ORM Issue
```python
# LEGACY (app.db.models) — 60+ tables, used by ETL/crawlers
from app.db.models import Tender, Award, APPRecord, KnowledgeEntry

# CANONICAL (app.models) — Modern, typed, used by API/agents  
from app.models.tender import Tender, TenderDocument
from models.boq import BOQItem, BOQComparison
from models.intelligence import KnowledgeEntry, PreComputedIntelligence
```

### Canonical Models (app.models/)

#### `base.py` — Mixins
```python
class UUIDMixin:
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)

class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)
```

#### `tender.py`
```python
class Tender(Base, TimestampMixin, UUIDMixin):
    __tablename__ = "tenders"
    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    tender_id: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(500))
    procuring_entity: Mapped[Optional[str]]
    district: Mapped[Optional[str]]
    division: Mapped[Optional[str]]
    estimated_cost: Mapped[Optional[float]]
    status: Mapped[TenderStatus] = mapped_column(default=TenderStatus.DRAFT)
    sor_agency: Mapped[str] = mapped_column(default="BWDB")
    zone: Mapped[Optional[str]]
    extracted_data: Mapped[Dict] = mapped_column(JSON, default=dict)
    comparison_results: Mapped[Dict] = mapped_column(JSON, default=dict)
```

#### `boq.py`
```python
class BOQItem(Base, TimestampMixin, UUIDMixin):
    __tablename__ = "boq_items"
    tender_id: Mapped[str] = mapped_column(ForeignKey("tenders.id"), index=True)
    code: Mapped[Optional[str]] = mapped_column(String(100), index=True)
    description: Mapped[str] = mapped_column(String(1000))
    unit: Mapped[Optional[str]]
    quantity: Mapped[Optional[float]]
    quoted_rate: Mapped[Optional[float]]
    sor_rate: Mapped[Optional[float]]
    sor_code: Mapped[Optional[str]]
    diff: Mapped[Optional[float]]
    pct_diff: Mapped[Optional[float]]
    flag: Mapped[Optional[str]] = mapped_column(index=True)
    work_type: Mapped[Optional[str]]
    section: Mapped[Optional[str]]
    agency: Mapped[Optional[str]]
```

#### `intelligence.py`
```python
class KnowledgeEntry(Base, TimestampMixin, UUIDMixin):
    __tablename__ = "knowledge_entries"
    tenant_id: Mapped[Optional[str]] = mapped_column(ForeignKey("tenants.id"))
    tender_id: Mapped[Optional[str]] = mapped_column(ForeignKey("tenders.tender_id"), index=True)
    entry_type: Mapped[str] = mapped_column(index=True)  # tender, boq, award, competitor, rate, report, opening
    title: Mapped[str] = mapped_column(String(500))
    content: Mapped[str] = mapped_column(Text)
    data: Mapped[Dict] = mapped_column(JSON, default=dict)
    summary: Mapped[str] = mapped_column(Text)
    source: Mapped[str]
    embedding_id: Mapped[Optional[str]] = mapped_column(index=True)
    tags: Mapped[List[str]] = mapped_column(JSON, default=list)
    agency: Mapped[Optional[str]]
    zone: Mapped[Optional[str]]
    procurement_type: Mapped[Optional[str]]
```

### Database Session
```python
# backend/app/db/database.py
engine = create_async_engine(DATABASE_URL, pool_size=20, max_overflow=40)
async_session_factory = async_sessionmaker(engine, expire_on_commit=False)

async def get_session() -> AsyncSession:
    async with async_session_factory() as session:
        yield session
```

### Alembic Migrations
```python
# alembic/env.py — Targets app.models.Base ONLY
# Missing: app.db.models tables (30+ tables untracked)
```

---

## 8. Background Workers (Celery) {#background-workers}

**Location**: `backend/app/workers/`

### Celery App
```python
# backend/app/workers/celery_app.py
celery_app = Celery("procureflow")
celery_app.config_from_object("app.workers.celery_config")

# Beat Schedule (hardcoded agent IDs — needs capability-based)
beat_schedule = {
    "tender-radar-every-30-min": {
        "task": "app.workers.tasks.agent_tasks.run_agent_pipeline",
        "schedule": 1800.0,
        "args": ("tender-radar", {}),
    },
    "award-intelligence-daily": {
        "task": "app.workers.tasks.agent_tasks.run_agent_pipeline",
        "schedule": crontab(hour=2, minute=0),
        "args": ("agent-014-award-intelligence", {}),
    },
}
```

### Task Modules
| Module | Tasks |
|--------|-------|
| `agent_tasks.py` | `run_agent_pipeline`, `run_single_agent`, `run_workflow` |
| `boq_tasks.py` | `compare_boq_task`, `generate_boq_reports` |
| `document_tasks.py` | `process_pdf`, `ocr_document`, `extract_tables` |
| `pipeline_tasks.py` | `run_multi_agent_workflow`, `run_ppr_evaluation` |
| `notification_tasks.py` | `send_email`, `send_webhook`, `send_alert` |
| `report_tasks.py` | `generate_executive_report`, `generate_slt_report` |

### Queue Strategy (Planned)
```
Queue: high     → Tender radar, alerts, critical notifications
Queue: default  → BOQ comparison, agent pipelines, document processing
Queue: low      → Report generation, ML training, bulk imports
```

---

## 9. Document Processing {#document-processing}

### PDF Extraction (pdfplumber)
```python
# Primary: Table extraction for BOQs
with pdfplumber.open(pdf_path) as pdf:
    for page in pdf.pages:
        tables = page.extract_tables()
        for table in tables:
            # Parse rows → BOQ items
            # Handles multi-column layouts
```

### Fallback: Text + Regex
```python
# When tables fail: text extraction + pattern matching
text = page.extract_text()
# Regex for item codes, descriptions, rates
```

### OCR (Tesseract)
```python
# For scanned PDFs
import pytesseract
text = pytesseract.image_to_string(image, lang='ben+eng')
```

### Vision LLM (GPT-4o / Claude)
```python
# Complex layouts, handwritten notes
response = await llm_service.vision_extract(image_path, prompt)
```

### Document Types
| Type | Code | Extraction Method |
|------|------|-------------------|
| NIT (Notice Inviting Tender) | `nit` | Text + regex |
| TDS (Tender Data Sheet) | `tds` | Text + regex (financial criteria) |
| BOQ (Bill of Quantities) | `boq` | **Table extraction (pdfplumber)** |
| Drawings | `drawing` | Vision LLM |
| Corrigendum | `corrigendum` | Text diff |
| Specifications | `specification` | Text + structure |

---

## 10. Authentication & Authorization {#authentication--authorization}

### JWT Token
```python
# backend/app/core/security.py
def create_token(user_id: str, tenant_id: str, role: str, scopes: List[str]) -> str:
    payload = {
        "sub": user_id,
        "tenant_id": tenant_id,
        "role": role,           # owner, admin, manager, estimator, viewer
        "scopes": scopes,       # ["read", "write", "admin", "tender:read", ...]
        "exp": datetime.utcnow() + timedelta(hours=24),
        "iat": datetime.utcnow(),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm="HS256")
```

### Middleware Auth Check
```python
# main.py lines 289-303
if (settings.REQUIRE_API_AUTH 
    and request.method != "OPTIONS"
    and request.url.path.startswith("/api")
    and not _is_public_api_path(request.url.path)
    and _authenticate_api_request(request) is None):
    return JSONResponse(status_code=401, content={"detail": "Authentication required"})
```

### Public API Prefixes (No Auth Required)
```python
PUBLIC_API_PREFIXES = [
    "/api/health",
    "/api/auth/login", "/api/auth/register",
    "/api/v1/auth/login", "/api/v1/auth/register",
]
```

### Role Scopes
```python
ROLE_SCOPES = {
    "owner":   ["*"],
    "admin":   ["read", "write", "admin", "tender:*", "agent:*", "report:*"],
    "manager": ["read", "write", "tender:read", "tender:write", "report:read"],
    "estimator": ["read", "write", "tender:read", "boq:compare", "sor:read"],
    "viewer":  ["read", "tender:read", "report:read"],
}
```

### Dependencies
```python
# security.py
async def require_scope(scope: str):
    # Checks user.scopes contains scope
    
async def require_role(role: str):
    # Checks user.role >= required role (hierarchy)
```

### RLS (Row-Level Security)
```sql
-- Migration 011: tenant_rbac_context
-- Sets app.current_tenant_id per request
-- Policies on all tenant-scoped tables:
CREATE POLICY tenant_isolation ON tenders
    USING (tenant_id = current_setting('app.current_tenant_id'));
```

---

## Component Interaction Diagram

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Frontend  │────▶│  API Gateway │────▶│  Agent Brain │
│  (Next.js)  │     │  (FastAPI)   │     │  (Orchestr.) │
└─────────────┘     └──────┬──────┘     └──────┬──────┘
                           │                   │
         ┌─────────────────┼───────────────────┼─────────────────┐
         ▼                 ▼                   ▼                 ▼
┌─────────────┐   ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  PostgreSQL │   │    Redis    │    │   MinIO     │    │  External   │
│  (Core DB)  │   │ (Streams/   │    │  (Reports,  │    │   APIs      │
│             │   │  Cache)     │    │   Uploads)  │    │  (e-GP)     │
└──────┬──────┘   └──────┬──────┘    └──────┬──────┘    └──────┬──────┘
       │                 │                  │                  │
       ▼                 ▼                  ▼                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    BACKGROUND WORKERS (Celery)                       │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐  │
│  │ Agent Tasks │ │ BOQ Tasks   │ │ Doc Tasks   │ │ Pipeline    │  │
│  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Related Documentation

- [Architecture Overview](../architecture/overview.md)
- [ADRs](../architecture/ADRs.md)
- [Integration Workflows](./integration-workflows.md)
- [API Documentation](../api/README.md)
- [Database Schema](../database/schema.md)