# ProcureFlow BD — Integration Workflows

## Overview
This document describes cross-system integration workflows and data flows between components.

---

## 1. e-GP Portal Integration

### 1.1 Tender Search & Monitoring
```
┌─────────────────────────────────────────────────────────────────┐
│                    TENDER RADAR WORKFLOW                         │
└─────────────────────────────────────────────────────────────────┘

Cron (every 30 min) / Manual Trigger
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│  TenderRadarAgent.execute()                                     │
│  • POST /TenderDetailsServlet (funName=AllTenders)              │
│    viewType: Live, Archive, AllTenders, Cancel                  │
│    pageNo: 1-100, size: 100                                     │
│  • Filter: category == "Works"                                  │
│  • For each tender: check if new/updated                        │
└─────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│  New tenders → brain.store_knowledge("tender", tender_id, ...)  │
│  Alert matches → NotificationTasks.send_email/webhook           │
└─────────────────────────────────────────────────────────────────┘
```

**Endpoints Used**:
| Operation | Endpoint | Method | Auth |
|-----------|----------|--------|------|
| Search Live | `/TenderDetailsServlet` | POST | No |
| Search Archive | `/TenderDetailsServlet` | POST | No |
| View Tender | `/ViewTender.jsp?id={ID}` | GET | No |

### 1.2 Tender Document Acquisition
```
┌─────────────────────────────────────────────────────────────────┐
│                  TENDER ACQUISITION WORKFLOW                     │
└─────────────────────────────────────────────────────────────────┘

TenderAcquisitionAgent.execute(tender_id)
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│  1. LOGIN (JSESSIONID seeding)                                   │
│     GET / → POST /LoginSrBean?action=checkLogin                  │
│     → GET /Index.jsp (bypass MobileNID)                          │
└─────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│  2. DOWNLOAD DOCUMENTS (parallel)                                │
│     • Notice PDF: /GeneratePdf?reqURL=...&id={ID}               │
│     • All Docs ZIP: /TenderSecUploadServlet?funName=zipdownload │
│     • Individual: /tenderer/TenderDocView.jsp?tenderId={ID}     │
└─────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│  3. EXTRACT & SHARE                                              │
│     • pdfplumber on BOQ (Section 6) → brain.store_knowledge()   │
│     • pdfplumber on TDS (Section 2) → brain.store_knowledge()   │
│     • Files saved to: uploads/{tender_id}/                       │
└─────────────────────────────────────────────────────────────────┘
```

**Subprocess Isolation**: `_sub_dl.py` runs as separate process to avoid WinError 10060.

### 1.3 Award Data Crawling
```
┌─────────────────────────────────────────────────────────────────┐
│                    AWARD CRAWL WORKFLOW                          │
└─────────────────────────────────────────────────────────────────┘

AwardIntelligenceAgent.execute()
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│  POST /SearchNoaServlet                                          │
│  • keyword: agency name (BWDB, LGED, PWD, etc.)                 │
│  • pageNo: 1-10, size: 100                                       │
│  • Parse HTML table → award records                              │
│  • Enrich: detail_url → ViewAwardedContracts.jsp                │
└─────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│  Store → awards table + knowledge_entries ("award" type)        │
│  Link: package_no → tender_id → app_id (lifecycle table)        │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2. BOQ Comparison Pipeline

### 2.1 File Upload Flow (Current)
```
┌─────────────────────────────────────────────────────────────────┐
│                  BOQ COMPARISON (SYNC)                           │
└─────────────────────────────────────────────────────────────────┘

POST /api/boq/compare
├── file: multipart/form-data (PDF/XLSX)
├── sor_agency: BWDB|PWD|LGED
├── zone: A|B|C|D
└── tender_info: {tender_id, package_no, title, ...}

         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│  1. Parse BOQ                                                    │
│     • PDF: pdfplumber.extract_tables()                          │
│     • XLSX: openpyxl                                            │
│     • Output: [{item_no, code, desc, unit, qty, quoted_rate}]  │
└─────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│  2. SOR Matching (per item × 3 agencies)                        │
│     FOR each item:                                               │
│       sor_service.find_rate(code, desc, sor_agency, zone)       │
│       → rate, sor_record, confidence                             │
│       → Compute diff, pct_diff, flag                            │
└─────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│  3. Generate Reports                                             │
│     • Excel: openpyxl (detailed + summary sheets)               │
│     • DOCX: python-docx (executive summary)                     │
│     • Save to: outputs/{boq_file_id}/                           │
└─────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│  4. Persist                                                      │
│     • BOQComparison record                                       │
│     • BOQItem records (cascade delete-orphan)                   │
└─────────────────────────────────────────────────────────────────┘
         │
         ▼
Response: {comparison_id, stats, excel_path, docx_path, items[]}
```

### 2.2 Brain Compare Flow (No Upload)
```
┌─────────────────────────────────────────────────────────────────┐
│                  BOQ COMPARISON (BRAIN)                          │
└─────────────────────────────────────────────────────────────────┘

POST /api/boq/brain-compare
{
    "tender_id": "1298004",
    "sor_agency": "BWDB",
    "zone": "A"
}

         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│  1. Query Brain                                                  │
│     brain.query_knowledge("boq_text", tender_id)                │
│     brain.query_knowledge("tds_text", tender_id)                │
│     brain.query_knowledge("tender_document", tender_id)         │
└─────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│  2. Extract BOQ from text                                        │
│     • Parse PDF text for items                                  │
│     • Extract TDS criteria for eligibility                      │
└─────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│  3. Same SOR matching + report generation as file upload        │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. Agent Pipeline Orchestration

### 3.1 Standard Pipeline
```
┌─────────────────────────────────────────────────────────────────┐
│              MULTI-AGENT WORKFLOW EXECUTION                      │
└─────────────────────────────────────────────────────────────────┘

WorkflowOrchestrator.run_workflow([
    {"agent_id": "tender-radar", "input": {"company_profile": {...}}},
    {"agent_id": "tender-acquisition", "depends_on": ["tender-radar"]},
    {"agent_id": "boq-intelligence", "depends_on": ["tender-acquisition"]},
    {"agent_id": "spec-intelligence", "depends_on": ["tender-acquisition"]},
    {"agent_id": "eligibility-compliance", "depends_on": ["tender-acquisition"]},
    {"agent_id": "rate-analysis", "depends_on": ["boq-intelligence"]},
    {"agent_id": "market-rate-intelligence", "depends_on": ["rate-analysis"]},
    {"agent_id": "award-intelligence", "depends_on": ["tender-acquisition"]},
    {"agent_id": "competitor-intelligence", "depends_on": ["award-intelligence"]},
    {"agent_id": "win-probability", "depends_on": ["rate-analysis", "competitor-intelligence"]},
    {"agent_id": "bid-position-optimizer", "depends_on": ["win-probability"]},
    {"agent_id": "executive-decision", "depends_on": ["win-probability", "bid-position-optimizer"]},
    {"agent_id": "report-generation", "depends_on": ["executive-decision"]}
])

Execution:
1. Topological sort by depends_on
2. Parallel execution where possible
3. Each agent: brain._message_handlers[agent_id](message)
4. Results passed via context[dep_id] = result
4. All results stored to agent_results table (shared session)
```

### 3.2 Idle Cycle (Background Intelligence)
```
┌─────────────────────────────────────────────────────────────────┐
│                    IDLE TIME CYCLE                               │
└─────────────────────────────────────────────────────────────────┘

AgentBrain._idle_time_cycle()  (runs every 5 min)

Cycle 0 (5 min):  Quick tender check
    → brain.get_agent("agent-038").execute({"action": "quick_check"})

Cycle 3 (15 min): Pre-screening
    → brain.get_agent("agent-038").execute({"action": "pre_screen"})

Cycle 6 (30 min): MOAT/SLT/NPPI analysis
    → brain.get_agent("agent-036").execute({"action": "idle_cycle"})

Cycle 12 (60 min): Full intelligence refresh
    → Multiple agents execute with {"action": "full_analysis"}
    → Results persisted to knowledge_entries + pre_computed_intelligence
```

---

## 4. Data Synchronization Flows

### 4.1 Crawl JSON → PostgreSQL Import
```
┌─────────────────────────────────────────────────────────────────┐
│              IMPORT_CRAWLED_INTELLIGENCE                         │
└─────────────────────────────────────────────────────────────────┘

python scripts/import_all_crawled_intelligence.py --skip-opening-reports

         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│  1. Scan crawl_output/NationalEGP/                              │
│     ├── Tenders/ (Live, Archive, AllTenders, Cancel)            │
│     ├── Awards/ (by agency keyword)                             │
│     ├── APP_BY_FY/ (13 FYs × 2 runs)                            │
│     ├── eExperience/ (completed, ongoing)                       │
│     └── OpeningReport/                                          │
└─────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│  2. Per file type → Domain service                               │
│     • Tenders → import_crawled_tender_data() → tenders table    │
│     • Awards  → import_crawled_award_data() → awards table      │
│     • APP     → import_crawled_app_data() → app_records table   │
│     • eExp    → import_eexperience_data() → knowledge_entries   │
└─────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│  3. Post-import reconciliation                                   │
│     • reconcile_awards_to_app_records() → lifecycle table       │
│     • rebuild_contractor_intelligence() → contractor_dna        │
│     • rebuild_procurement_lifecycle() → complete chains         │
└─────────────────────────────────────────────────────────────────┘
```

### 4.2 Award Package Number Repair
```
┌─────────────────────────────────────────────────────────────────┐
│              REPAIR_AWARD_PACKAGE_NUMBERS                        │
└─────────────────────────────────────────────────────────────────┘

python scripts/repair_award_package_numbers_from_crawl.py

         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│  1. Load unresolved queue (52K+ records)                        │
│     runtime/crawl_audit/unresolved_award_recrawl_queue.json     │
└─────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│  2. Cross-reference with crawl data                              │
│     • Search crawl_output/NationalEGP/Awards/ for tender_id     │
│     • Extract package_no from award records                     │
│     • Match by tender_id + contractor_name + amount             │
└─────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│  3. Update awards table                                          │
│     UPDATE awards SET package_no = :repaired WHERE id = :id     │
└─────────────────────────────────────────────────────────────────┘
```

---

## 5. External API Integrations

### 5.1 LLM Providers
```
┌─────────────────────────────────────────────────────────────────┐
│                    LLM SERVICE ROUTING                           │
└─────────────────────────────────────────────────────────────────┘

LLMService.generate(prompt, provider="auto")

provider="auto" → Priority:
  1. Anthropic Claude (if ANTHROPIC_API_KEY) — structured JSON
  2. OpenAI GPT-4o (if OPENAI_API_KEY) — fallback
  3. Ollama local (if OLLAMA_BASE_URL reachable) — private/offline

Specialized methods:
  • generate_structured(prompt, schema) → JSON output validation
  • embed(texts) → vector embeddings
  • vision_extract(image_path, prompt) → OCR + understanding
```

### 5.2 MinIO File Storage
```
┌─────────────────────────────────────────────────────────────────┐
│                    FILE STORAGE FLOW                             │
└─────────────────────────────────────────────────────────────────┘

Bucket: procureflow
├── uploads/{tender_id}/           # Raw tender documents
├── outputs/{boq_file_id}/         # Generated Excel/DOCX reports
├── templates/                     # Report templates
├── embeddings/                    # Vector index files
└── exports/                       # Bulk data exports

Operations:
  • PUT /{bucket}/{key}           # Upload
  • GET /{bucket}/{key}           # Download (presigned URLs)
  • DELETE /{bucket}/{key}        # Cleanup
```

### 5.3 Webhook Delivery
```
┌─────────────────────────────────────────────────────────────────┐
│                    WEBHOOK EVENT FLOW                            │
└─────────────────────────────────────────────────────────────────┘

Agent completes → BaseAgent._schedule_result_webhook()

WEBHOOK_AGENT_EVENTS=1 enables:
  Event Types:
    • agent.completed
    • agent.failed
    • tender.discovered
    • award.updated
    • boq.compared

Payload:
{
  "event_id": "uuid",
  "event_type": "agent.completed",
  "timestamp": "2024-06-15T10:30:00Z",
  "payload": {
    "agent_id": "rate-analysis",
    "tender_id": "1298004",
    "status": "success",
    "execution_time_ms": 1250
  }
}

Delivery: POST to configured webhook URLs (per tenant)
Retry: Exponential backoff (3 attempts)
Dead Letter: Failed deliveries logged for manual replay
```

---

## 6. Database Cross-Reference Patterns

### 6.1 Universal Join Keys
```sql
-- Primary linkage across all procurement tables
package_no (normalized) + work_name

-- Normalization function:
CREATE OR REPLACE FUNCTION normalize_package(p_text text)
RETURNS text AS $$
  SELECT upper(regexp_replace(p_text, '[^A-Z0-9/._-]', '', 'g'))
$$ LANGUAGE sql;

-- Usage:
-- tenders.package_no ↔ awards.package_no ↔ app_records.package_no
-- lifecycle.app_id ↔ app_records.app_id
-- lifecycle.tender_id ↔ tenders.tender_id
-- lifecycle.award_tender_id ↔ awards.tender_id
```

### 6.2 Knowledge Entry Linkage
```sql
-- knowledge_entries links to everything via tender_id + entry_type
SELECT * FROM knowledge_entries 
WHERE tender_id = '1298004' 
  AND entry_type IN ('boq_text', 'tds_text', 'award', 'competitor');

-- Vector search via project_memory (pgvector)
SELECT * FROM knowledge_entries ke
JOIN vector_index vi ON ke.embedding_id = vi.id
WHERE vi.embedding <=> query_embedding < 0.3;
```

---

## 7. Error Handling & Retry Patterns

### 7.1 Crawler Resilience
```python
# TenderDetailsServlet with retry
async def fetch_with_retry(client, url, data, retries=3, timeout=25):
    for attempt in range(retries):
        try:
            return await client.post(url, data=data, timeout=timeout)
        except (httpx.TimeoutException, httpx.ConnectError) as e:
            if attempt == retries - 1:
                raise
            await asyncio.sleep(1 + attempt)  # Exponential backoff
```

### 7.2 Agent Execution Safety
```python
# BaseAgent.run() wrapper
async def run(self, context):
    try:
        result = await self.execute(context)
        # Persist success
    except Exception as e:
        # Create FAILED AgentResult
        # Log error with trace_id
        # Still persist to DB for debugging
        # Optional: trigger alert webhook
```

### 7.3 Database Transaction Safety
```python
# Shared session pattern (orchestrator)
async with session_factory() as session:
    for agent in workflow:
        result = await agent.run(context, session=session)
        # All agents share same transaction
    await session.commit()  # Single commit
```

---

## 8. Monitoring Integration Points

### 8.1 Health Checks
```
GET /api/health
{
  "status": "healthy",
  "api_routers_loaded": true,
  "agent_runtime_ready": true,
  "db_connected": true,
  "redis_connected": true,
  "minio_connected": true
}

GET /api/health/db     → Pool stats, active connections
GET /api/health/agents → Registered agents, brain queue size
GET /api/health/celery → Worker status, queue depths
```

### 8.2 Key Metrics
| Metric | Source | Alert Threshold |
|--------|--------|-----------------|
| API latency p95 | FastAPI middleware | > 5s |
| BOQ compare duration | Celery task timing | > 120s |
| Agent pipeline duration | AgentBrain workflow | > 300s |
| Crawler success rate | Crawl checkpoint | < 90% |
| DB pool usage | SQLAlchemy pool | > 80% |
| Knowledge store size | AgentBrain stats | > 1800/2000 |

---

## Related Documentation

- [Architecture Overview](../architecture/overview.md)
- [Component Documentation](../architecture/components.md)
- [ADRs](../architecture/ADRs.md)
- [API Documentation](../api/README.md)
- [Database Schema](../database/schema.md)