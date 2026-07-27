# Knowledge API Contract

**Router**: `/api/v1/knowledge`  
**Tags**: `knowledge`  
**Auth**: JWT (tenant-scoped)

---

## Overview

Knowledge API for **enterprise knowledge management**, **search intelligence**, and **knowledge lake operations** across the AI agent system. Core to **AgentBrain** and **knowledge sharing** across all agents (tender acquisition, BOQ processing, SOR matching, etc.).

**Primary Use Cases**:
- Search and retrieve knowledge across all agent domains
- Share knowledge between agents (BOQ → TDS → CORRECTIONS)
- Manage knowledge versioning and lifecycle
- Knowledge lake operations (storage, indexing, retrieval)
- AI model training data management

---

## Endpoint Catalog

| Method | Path | Purpose | Auth |
|--------|------|---------|------|
| GET | `/knowledge/search` | Search knowledge across all domains | JWT |
| GET | `/knowledge/entries` | List knowledge entries with filters | JWT |
| GET | `/knowledge/entry/{type}/{id}` | Get specific knowledge entry | JWT |
| POST | `/knowledge/share` | Share knowledge with metadata | JWT |
| POST | `/knowledge/retrieve` | Retrieve knowledge by query | JWT |
| GET | `/knowledge/stats` | Knowledge system statistics | JWT |
| POST | `/knowledge/train-model` | Train AI model from knowledge | JWT |

---

## Request/Response Schemas

### `GET /knowledge/search`

**Query Parameters**
| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `q` | string | `""` | Search query (full-text search across title, summary, content) |
| `type` | string | `""` | Filter by entry type (`tender_document`, `boq_text`, `tds_text`, `sor_rates`, `agent_log`) |
| `tender_id` | string | `""` | Filter by tender ID |
| `agent_id` | string | `""` | Filter by agent source |
| `created_after` | string | `""` | Filter by creation date (ISO format) |
| `created_before` | string | `""` | Filter by creation date (ISO format) |
| `page` | int | 1 | Page number |
| `limit` | int | 50 | Results per page (1-100) |

**Response (200)**
```json
{
  "success": true,
  "query": "bridge construction",
  "results": {
    "tender_document": [
      {
        "id": "uuid",
        "title": "Construction of Bridge",
        "summary": "Major bridge construction project",
        "tender_id": "1290886",
        "agent_id": "agent-002-tender-acquisition",
        "created_at": "2026-07-21T10:30:00Z",
        "updated_at": "2026-07-21T10:35:12Z",
        "file_path": "uploads/1290886/notice.pdf",
        "processing_status": "completed",
        "confidence_score": 0.94,
        "tags": ["bridge", "construction", "chattogram"],
        "source_system": "AgentBrain"
      }
    ],
    "boq_text": [
      {
        "id": "uuid",
        "title": "BOQ - Bridge Construction",
        "summary": "Earthwork excavation: 5000 m3 at 185.50 BDT/m3",
        "tender_id": "1290886",
        "agent_id": "agent-005-boq-intelligence",
        "created_at": "2026-07-21T10:32:45Z",
        "extracted_from": "uploads/1290886/boq.pdf",
        "format": "tabular",
        "tables_extracted": 3,
        "confidence_score": 0.92
      }
    ],
    "tds_text": [
      {
        "id": "uuid",
        "title": "TDS - Bridge Construction",
        "summary": "Tender security: 1% of estimated cost (45000000 BDT)",
        "tender_id": "1290886",
        "agent_id": "agent-004-document-ai",
        "created_at": "2026-07-21T10:31:20Z",
        "extracted_from": "uploads/1290886/tds.pdf",
        "criteria_count": 7,
        "confidence_score": 0.98
      }
    ],
    "sor_rates": [],
    "agent_log": []
  },
  "pagination": {
    "page": 1,
    "limit": 50,
    "total": 2,
    "total_pages": 1,
    "has_next": false,
    "has_prev": false
  },
  "facets": {
    "entry_type": {
      "tender_document": 1,
      "boq_text": 1,
      "tds_text": 1
    },
    "agent_id": {
      "agent-002-tender-acquisition": 1,
      "agent-005-boq-intelligence": 1,
      "agent-004-document-ai": 1
    },
    "confidence": {
      "high": [0.90, 1.0]: 2,
      "medium": [0.70, 0.89]: 0,
      "low": [0.0, 0.69]: 0
    }
  }
}
```

### `GET /knowledge/entries`

**Query Parameters**
| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `type` | string | `""` | Comma-separated entry types |
| `created_after` | string | `""` | ISO date |
| `created_before` | string | `""` | ISO date |
| `limit` | int | 50 | Max results (1-500) |
| `offset` | int | 0 | Pagination offset |

**Response (200)**
```json
{
  "success": true,
  "entries": [
    {
      "id": "uuid",
      "type": "tender_document",
      "tender_id": "1290886",
      "tender_public_id": "1290886",
      "title": "Construction of Bridge",
      "summary": "Major bridge construction project for Chattogram port area",
      "agent_id": "agent-002-tender-acquisition",
      "agent_name": "Tender Acquisition Agent",
      "created_at": "2026-07-21T10:30:00Z",
      "updated_at": "2026-07-21T10:35:12Z",
      "file_path": "uploads/1290886/notice.pdf",
      "file_size": 1024000,
      "processing_status": "completed",
      "confidence_score": 0.94,
      "tags": ["bridge", "construction", "chattogram"],
      "downloaded_files": ["notice.pdf"],
      "extracted_fields": {
        "procuring_entity": "BWDB Dhaka Division",
        "estimated_cost": 45000000,
        "tender_security": 450000,
        "package_no": "BWDB-DHA-01/2024-25",
        "closing_date": "2026-08-15"
      },
      "validation_status": "PASSED",
      "confidence_breakdown": {
        "ocr": 0.98,
        "nlu": 0.92,
        "structure": 0.95
      },
      "pipeline_steps": [
        "document_received",
        "ocr_extraction",
        "natural_language_understanding",
        "structure_validation",
        "knowledge_storage"
      ],
      "source_system": "AgentBrain",
      "model_version": "v2.1.0"
    }
  ],
  "total": 1,
  "limit": 50,
  "offset": 0
}
```

### `GET /knowledge/entry/{type}/{id}`

**Path Params**
- `type`: `tender_document|boq_text|tds_text|sor_rates|agent_log`
- `id`: Knowledge entry UUID

**Response (200)**
```json
{
  "success": true,
  "entry": {
    "id": "uuid",
    "type": "tender_document",
    "tender_id": "1290886",
    "tender_public_id": "1290886",
    "title": "Construction of Bridge",
    "summary": "Major bridge construction project for Chattogram port area",
    "agent_id": "agent-002-tender-acquisition",
    "agent_name": "Tender Acquisition Agent",
    "created_at": "2026-07-21T10:30:00Z",
    "updated_at": "2026-07-21T10:35:12Z",
    "file_path": "uploads/1290886/notice.pdf",
    "file_size": 1024000,
    "processing_status": "completed",
    "confidence_score": 0.94,
    "tags": ["bridge", "construction", "chattogram"],
    "downloaded_files": ["notice.pdf"],
    "extracted_fields": { ... },
    "validation_status": "PASSED",
    "confidence_breakdown": { ... },
    "pipeline_steps": [ ... ],
    "source_system": "AgentBrain",
    "model_version": "v2.1.0",
    "metadata": {
      "ocr_engine": "tesseract-5.0",
      "preprocessing": "adaptive_threshold",
      "postprocessing": "spell_check+ner"
    },
    "related_entries": [
      {"id": "uuid", "type": "boq_text", "title": "BOQ - Bridge Construction"}
    ]
  }
}
```

### `POST /knowledge/share`

**Request**
```json
{
  "type": "tender_document",
  "tender_id": "1290886",
  "title": "Construction of Bridge",
  "summary": "Major bridge construction project for Chattogram port area",
  "agent_id": "agent-002-tender-acquisition",
  "extracted_fields": { ... },
  "extracted_text": "Extracted tender description...",
  "tags": ["bridge", "construction", "chattogram"],
  "file_paths": {"notice": "uploads/1290886/notice.pdf"},
  "downloaded_files": ["notice.pdf"],
  "confidence_score": 0.94,
  "model_version": "v2.1.0",
  "processing_details": {
    "ocr_engine": "tesseract-5.0",
    "pages_processed": 42,
    "extracted_tables": 3
  },
  "validation_result": {
    "status": "PASSED",
    "violations": [],
    "compliance_score": 0.98
  },
  "source_system": "AgentBrain",
  "metadata": {"tender_source": "e-GP", "extraction_method": "pdfplumber"}
}
```

**Response (200)**
```json
{
  "success": true,
  "entry": {
    "id": "uuid",
    "type": "tender_document",
    "tender_id": "1290886",
    "title": "Construction of Bridge",
    "summary": "Major bridge construction project for Chattogram port area",
    "agent_id": "agent-002-tender-acquisition",
    "created_at": "2026-07-21T10:40:00Z",
    "updated_at": "2026-07-21T10:40:00Z",
    "file_path": "uploads/1290886/notice.pdf",
    "processing_status": "completed",
    "confidence_score": 0.94,
    "source_system": "AgentBrain"
  },
  "message": "Knowledge entry created and shared with agent system",
  "next_actions": [
    "Notified AgentBrain cache",
    "Updated knowledge graph",
    "Scheduled knowledge validation"
  ]
}
```

### `POST /knowledge/retrieve`

**Request**
```json
{
  "tender_id": "1290886",
  "query": "financial requirements",
  "entry_types": ["tds_text", "boq_text"],
  "max_chars": 50000,
  "keywords": ["security", "turnover", "experience"],
  "format": "structured"
}
```

**Response (200)**
```json
{
  "success": true,
  "tender_id": "1290886",
  "retrieved_entries": [
    {
      "id": "uuid",
      "type": "tds_text",
      "title": "TDS - Bridge Construction",
      "extracted_fields": {
        "general_experience_years": 12,
        "annual_turnover_bdt": 55000000,
        "tender_security_percent": 1.0,
        "liquid_assets_bdt": 28000000,
        "minimum_tender_capacity_bdt": 500000,
        "performance_security_percent": 5.0
      },
      "extracted_text": "Page 1: BID NOTICE...\n\n1. General Experience: Minimum 12 years...\n\n2. Annual Turnover: Tk. 55,00,000...\n\n3. Liquid Assets: Tk. 28,00,000...",
      "confidence_score": 0.98,
      "relevance_score": 0.95
    },
    {
      "id": "uuid",
      "type": "boq_text",
      "title": "BOQ - Bridge Construction",
      "extracted_fields": {
        "earthwork": {"quantity": 5000, "rate": 185.5, "unit": "m3"},
        "concrete": {"quantity": 500, "rate": 8000, "unit": "m3"}
      },
      "extracted_text": "Section 6 - BOQ\n\n1. Earthwork excavation: 5000 m3 at 185.50 BDT/m3\n\n2. Concrete works: 500 m3 at 8000 BDT/m3",
      "confidence_score": 0.92,
      "relevance_score": 0.88
    }
  ],
  "total_chars": 12500,
  "sources": [
    {"entry_id": "uuid", "type": "tds_text", "agent_id": "agent-004-document-ai"},
    {"entry_id": "uuid", "type": "boq_text", "agent_id": "agent-005-boq-intelligence"}
  ],
  "query_summary": {
    "keywords_found": ["security", "turnover", "experience"],
    "entry_types_covered": ["tds_text", "boq_text"],
    "overall_relevance": 0.92
  }
}
```

### `GET /knowledge/stats`

**Response (200)**
```json
{
  "success": true,
  "stats": {
    "total_entries": 1247,
    "by_type": {
      "tender_document": 847,
      "boq_text": 412,
      "tds_text": 398,
      "sor_rates": 23,
      "agent_log": 57
    },
    "by_agent": {
      "agent-002-tender-acquisition": 847,
      "agent-005-boq-intelligence": 412,
      "agent-004-document-ai": 398,
      "agent-011-rate-analysis": 23,
      "agent-027-orchestrator": 57
    },
    "processing_status": {
      "completed": 1239,
      "processing": 8,
      "failed": 0
    },
    "quality_metrics": {
      "avg_confidence_score": 0.95,
      "min_confidence_score": 0.78,
      "max_confidence_score": 0.99,
      "confidence_distribution": {
        "0.90_to_0.99": 987,
        "0.80_to_0.89": 245,
        "0.70_to_0.79": 15
      }
    },
    "storage_usage": {
      "total_size_bytes": 45761234,
      "breakdown_by_type": {
        "tender_document": 23456789,
        "boq_text": 12345678,
        "tds_text": 8912345
      }
    },
    "last_updated": "2026-07-21T12:00:00Z"
  }
}
```

### `POST /knowledge/train-model`

**Request**
```json
{
  "model_type": "lightgbm|random_forest|neural_network",
  "entry_types": ["tds_text", "boq_text"],
  "target_fields": [
    "win_probability",
    "optimal_bid",
    "bid_strategy"
  ],
  "training_params": {
    "test_size": 0.2,
    "cross_validation_folds": 5,
    "hyperparameters": {"n_estimators": 200, "max_depth": 10}
  },
  "retrain": true,
  "model_id": "win_probability_model_v2.1"
}
```

**Response (200)**
```json
{
  "success": true,
  "model_training": {
    "status": "completed",
    "model_id": "win_probability_model_v2.1",
    "model_type": "gradient_boosting",
    "performance_metrics": {
      "accuracy": 0.87,
      "precision": 0.85,
      "recall": 0.82,
      "f1_score": 0.84,
      "auc_roc": 0.91
    },
    "training_info": {
      "samples_used": 1247,
      "training_time_seconds": 3600,
      "data_sources": ["tender_document", "boq_text", "tds_text"],
      "features_used": 45
    },
    "deployment_status": "ready",
    "next_schedule": "2026-08-21T10:00:00Z"
  },
  "message": "Model trained successfully and deployed to agent system",
  "next_steps": [
    "Updating AgentBrain with new model",
    "Scheduling periodic retraining",
    "Updating documentation"
  ]
}
```

---

## Error Codes

| Code | HTTP | Scenario |
|------|------|----------|
| `KNOWLEDGE_ENTRY_NOT_FOUND` | 404 | Knowledge entry not found |
| `KNOWLEDGE_INVALID_TYPE` | 400 | Invalid entry type |
| `KNOWLEDGE_DUPLICATE_ENTRY` | 409 | Entry already exists |
| `KNOWLEDGE_TRAINING_FAILED` | 500 | Model training error |

---

## Permission Requirements

| Endpoint | Role | Notes |
|----------|------|-------|
| All (except `/stats`) | `viewer` or higher | Access to knowledge entries |
| `/share`, `/retrieve` | `estimator` or `admin` | Write and modify knowledge |
| `/train-model` | `admin` | Model training privileges |

---

## Rate Limits

| Endpoint | Limit | Window |
|----------|-------|--------|
| `/search` | 120 | 60 |
| `/entries` | 60 | 60 |
| `/entry` | 60 | 60 |
| `/share` | 20 | 60 |
| `/retrieve` | 40 | 60 |
| `/stats` | 30 | 60 |

---

## Caching

- `GET /search`: `private, max-age=30` (live knowledge updates)
- `GET /entries`: `private, max-age=60` (slow-changing knowledge)
- `GET /entry`: `private, max-age=300` (frequently accessed entries)
- Other: `private, max-age=60`

---

## React Query Mapping

```typescript
export const knowledgeKeys = {
  all: () => ['knowledge'] as const,
  search: (params: KnowledgeSearchParams) => 
    [...knowledgeKeys.all, 'search', params] as const,
  entries: (params: KnowledgeListParams) =>
    [...knowledgeKeys.all, 'entries', params] as const,
  entry: (type: string, id: string) => 
    [...knowledgeKeys.all, 'entry', { type, id }] as const,
  stats: () => [...knowledgeKeys.all, 'stats'] as const,
  trainModel: () => [...knowledgeKeys.all, 'trainModel'] as const,
};

export function useKnowledgeSearch(params: KnowledgeSearchParams) {
  return useQuery({
    queryKey: knowledgeKeys.search(params),
    queryFn: () => apiFetch<KnowledgeSearchResponse>('/knowledge/search', { params }),
    staleTime: 30_000,
  });
}

export function useKnowledgeStats() {
  return useQuery({
    queryKey: knowledgeKeys.stats(),
    queryFn: () => apiFetch<KnowledgeStatsResponse>('/knowledge/stats'),
    staleTime: 300_000,
  });
}
```

---

## Integration Points

### AgentBrain ↔ Knowledge API
```
Agent-002-TenderAcquisition
  ↓ Shares knowledge
POST /knowledge/share → Redis+KGC+PostgreSQL

Agent-005-BOQIntelligence
  ↓ Retrieves knowledge
POST /knowledge/retrieve → Structured data for matching

Agent-004-DocumentAI
  ↓ Stores extracted text
POST /knowledge/share → TDS/BOQ text storage

Agent-011-RateAnalysis
  ↓ Retrieves financial criteria
GET /knowledge/entry/{id}/tds_text → Compliance rules
```

### Intelligence Collection Pipeline
```
Document Processing
  ↓ Extract text → TDS/BOQ
POST /knowledge/share → Knowledge storage

Knowledge Search
  ↓ Find relevant entries
GET /knowledge/search → Search across all domains

Model Training
  ↓ Learn from historical data
POST /knowledge/train-model → AI model updates
```

---

## Versioning

- `v1`: Current (PostgreSQL + Redis knowledge store)
- `v2` (planned): GraphQL knowledge queries, event-driven updates

---

## Configuration Options

Environment variables:
- `KNOWLEDGE_SEARCH_LIMIT=1000` (default: 500)
- `KNOWLEDGE_CACHE_TTL=3600` (seconds)
- `KNOWLEDGE_MAX_FILE_SIZE=10485760` (10MB)
- `KNOWLEDGE_MIN_CONFIDENCE=0.70` (threshold)

---

## Monitoring & Telemetry

**Metrics**:
- Knowledge entry creation/retrieval rates
- Confidence score distribution
- Cache hit/miss ratios
- Processing time per entry type
- Storage usage growth

**Alerts**:
- Confidence score < 0.70
- Processing time > 30 seconds
- Storage limit approaching

> **Dependency**: `app/agents/core/brain.py` (AgentBrain integration)
> **Integration**: `app/models/knowledge_graph.py` (knowledge graph updates)
> **Queue**: `workers/tasks/knowledge_tasks.py` (background knowledge processing)

---

## OpenAPI Reference

See `/openapi.json#/paths/~1api~1knowledge~1search`