# Document AI API Contract

**Router**: `/api/v1/tender-docs`  
**Tags**: `tender-docs`  
**Auth**: JWT (tenant-scoped)

---

## Overview

Document AI API for **Section2 (TDS) extraction** and **PDF document processing** in the e-GP tender workflow. Core component of the Tender Acquisition Agent (Agent-002) and BOQ comparison pipeline.

**Primary Use Cases**:
- Extract financial criteria from Section2 PDFs (TDS)
- Process all 11 document types from e-GP
- Upload and extract BOQ tables from PDFs
- Validate document completeness and compliance

---

## Endpoint Catalog

| Method | Path | Purpose | Auth |
|--------|------|---------|------|
| POST | `/tender-docs/extract` | Extract structured data from PDF/DOCX (TDS/BOQ) | JWT |
| GET | `/tender-docs/extract/{tender_id}` | Retrieve last extraction result | JWT |
| POST | `/tender-docs/process-bulk` | Process multiple documents asynchronously | JWT |
| GET | `/tender-docs/status/{job_id}` | Poll batch processing job status | JWT |
| GET | `/tender-docs/rules/{document_type}` | Get extraction rules for document type | Public |
| POST | `/tender-docs/validate` | Validate extracted data against PPR2025 rules | JWT |
| GET | `/tender-docs/health` | Service health and supported formats | Public |

---

## Request/Response Schemas

### `POST /tender-docs/extract`

**Request**
```json
{
  "tender_id": "1290886",
  "document_type": "tds|boq|notice|tds_2|sor|instructions",
  "file": "base64-encoded PDF/DOCX content",
  "confidence_threshold": 0.42,
  "extract_sections": ["financial", "schedule", "specifications"],
  "regime": "PPR2025|INDIAN_CONTRACT|STANDARD",
  "language": "en|bn"
}
```

**Response (202 - Async Job)**
```json
{
  "job_id": "uuid",
  "status_url": "/api/v1/tender-docs/status/uuid",
  "estimated_duration": "PT2M",
  "features": {
    "pdfplumber_extraction": true,
    "ocr_fallback": true,
    "ml_enhancement": true,
    "table_detection": true,
    "structure_validation": true
  }
}
```

**Sync Fallback (if `DOCUMENT_AI_SYNC_FALLBACK` set)**:
```json
{
  "success": true,
  "tender_id": "1290886",
  "document_type": "tds",
  "extracted_fields": {
    "general_experience_years": 12,
    "specific_experience_contracts": 3,
    "annual_turnover_bdt": 55000000,
    "liquid_assets_bdt": 28000000,
    "minimum_tender_capacity_bdt": 500000,
    "tender_security_percent": 1.0,
    "performance_security_percent": 5.0
  },
  "structured_data": {
    "experience": {
      "general": {"years": 12, "certifications": []},
      "specific": [{"project": "Bridge Construction", "value": 500000, "period": "2024-2025"}]
    },
    "financial": { ... },
    "technical": { ... }
  },
  "confidence": 0.94,
  "processing_time_ms": 1250,
  "format_used": "pdfplumber",
  "ocr_engine": "tesseract",
  "parser_version": "v2.1.0"
}
```

### `GET /tender-docs/extract/{tender_id}`

**Query Parameters**
| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `document_type` | string | null | Filter by type (tds/boq/notice/etc.) |
| `include_raw_text` | boolean | false | Include full OCR text |
| `sections` | string | null | Comma-separated sections to include |

**Response (200)**
```json
{
  "success": true,
  "tender_id": "1290886",
  "document_type": "tds",
  "extracted_at": "2026-07-21T10:30:00Z",
  "source_file": "uploads/1290886/tds.pdf",
  "processing_pipeline": [
    "preprocessing",
    "page_detection",
    "table_extraction",
    "ocr",
    "nlp_structure"
  ],
  "extracted_fields": { ... }, // Full TDS financial criteria
  "structured_data": { ... },
  "metadata": {
    "pages_processed": 42,
    "confidence_scores": {"financial": 0.94, "technical": 0.87},
    "warnings": ["Page 12: Quality scan - low contrast"],
    "ocr_engine": "tesseract-5.0",
    "model_version": "v2.1.0-enhanced"
  },
  "validation_status": "PASSED",
  "compliance_issues": [],
  "regime": "PPR2025",
  "language": "en",
  "extracted_text_sample": "Page 1: BID NOTICE..."
}
```

### `POST /tender-docs/process-bulk`

**Request**
```json
{
  "tender_id": "1290886",
  "documents": [
    {
      "document_type": "tds",
      "file_name": "tender_tds_1290886.pdf",
      "content": "base64...",
      "priority": 1,
      "extract_criteria": ["financial", "specifications"]
    },
    {
      "document_type": "boq",
      "file_name": "tender_boq_1290886.pdf",
      "content": "base64...",
      "priority": 2
    }
  ],
  "async": true
}
```

**Response (202)
```json
{
  "job_id": "uuid",
  "status_url": "/api/v1/tender-docs/status/uuid",
  "documents_processed": 2,
  "estimated_completion": "2026-07-21T10:35:00Z",
  "started_at": "2026-07-21T10:32:00Z"
}
```

### `GET /tender-docs/status/{job_id}`

**Response (200)**
```json
{
  "job_id": "uuid",
  "status": "PENDING|RUNNING|SUCCESS|FAILED",
  "progress": 0-100,
  "documents": [
    {
      "id": "doc1",
      "type": "tds",
      "status": "SUCCESS|FAILED",
      "extracted_fields": { ... } if SUCCESS,
      "error_message": "Page 5: Unrecoverable OCR error" if FAILED
    }
  ],
  "overall_success": true,
  "started_at": "2026-07-21T10:32:00Z",
  "completed_at": "2026-07-21T10:35:12Z",
  "processing_time_ms": 2800
}
```

### `GET /tender-docs/rules/{document_type}`

**Path Params**
- `document_type`: `tds|boq|notice|instructions|sor|sds|specifications|drawings|appendix`

**Response (200)**
```json
{
  "document_type": "tds",
  "rules_version": "v2.1.0",
  "extraction_schema": {
    "required_fields": [
      "general_experience_years",
      "specific_experience_contracts",
      "annual_turnover_bdt",
      "liquid_assets_bdt",
      "minimum_tender_capacity_bdt",
      "tender_security_percent",
      "performance_security_percent"
    ],
    "field_types": {
      "general_experience_years": "integer",
      "annual_turnover_bdt": "currency",
      "tender_security_percent": "percentage"
    },
    "regex_patterns": {
      "indian_numbering": "\\d{1,3}(,\d{2})*(\.\d+)?",
      "percentage": "\\d+(\\.\\d+)?%"
    },
    "validation_rules": {
      "min_age_experience": 5,
      "min_turnover": 5000000,
      "max_security_percent": 10
    }
  },
  "tbs_patterns": [
    "shall be (\\d+) years",
    "value of at least Tk. (\\d+,\\d+)",
    "average annual construction turnover greater than Tk (\\d+,\\d+)"
  ],
  "fallback_patterns": {
    "liquid_assets": "liquid assets.*?Tk. (\\d+,\\d+)",
    "min_capacity": "minimum tender capacity.*?(\\d+,\\d+)"
  }
}
```

### `POST /tender-docs/validate`

**Request**
```json
{
  "tender_id": "1290886",
  "document_type": "tds",
  "extracted_fields": {
    "general_experience_years": 12,
    "annual_turnover_bdt": 55000000,
    "tender_security_percent": 1.0
  },
  "regime": "PPR2025",
  "check_violations": true,
  "compliance_framework": "SLT|ALT|PPR2025"
}
```

**Response (200)
```json
{
  "success": true,
  "validation_passed": true,
  "violations": [],
  "compliance_score": 0.94,
  "recommendations": [
    "All financial criteria meet PPR2025 minimum requirements",
    "Tender security at 1% is within acceptable range (max 2%)",
    "Document completeness: 100%"
  ],
  "details": {
    "matched_rules": [
      "Rule 28(2): Annual turnover requires minimum Tk. 5,000,000",
      "Rule 28(4): Experience minimum 5 years"
    ],
    "partial_matches": [],
    "unmatched_fields": []
  }
}
```

### `GET /tender-docs/health`

**Response (200)
```json
{
  "status": "healthy",
  "version": "v2.1.0",
  "supported_formats": [
    "pdf",
    "docx",
    "tiff",
    "png"
  ],
  "services": {
    "pdfplumber": { "available": true, "version": "0.8.6" },
    "tesseract": { "available": true, "version": "5.0" },
    "rapidfuzz": { "available": true },
    "ollama": { "available": true, "models": ["nomic-embed-text"] }
  },
  "extraction_capabilities": {
    "tds_financial_criteria": true,
    "boq_table_parsing": true,
    "multi_column_layout": true,
    "indian_numbering_recognition": true,
    "schedule_of_rates_matching": true,
    "natural_language_structure": true
  }
}
```

---

## Error Codes

| Code | HTTP | Scenario |
|------|------|----------|
| `TD_SUPPORTED_FORMATS` | 415 | File format not supported |
| `TD_EXTRACTION_FAILED` | 400 | OCR or parsing failed |
| `TD_RATES_NOT_FOUND` | 404 | No extraction found for tender/document |
| `TD_JOB_NOT_FOUND` | 404 | Job ID not found |
| `TD_JOB_NOT_READY` | 409 | Job still running |
| `TD_VALIDATION_FAILED` | 422 | Extracted data doesn't meet PPR2025 rules |

---

## Permission Requirements

| Endpoint | Role | Notes |
|----------|------|-------|
| All (except health) | `viewer` or higher | Tenant-scoped |
| `/extract`, `/process-bulk` | `estimator` or `compliance` | Write access required |

---

## Rate Limits

| Endpoint | Limit | Window |
|----------|-------|--------|
| `/extract` | 20 | 60 |
| `/process-bulk` | 5 | 300 |
| `/status` | 60 | 60 |

---

## Caching

- `GET /rules/{type}`: `public, max-age=3600` (rules rarely change)
- `GET /health`: `public, max-age=30` |
- Other: `private, max-age=30` or `no-store`

---

## React Query Mapping

```typescript
export const tenderDocsKeys = {
  all: () => ['tender-docs'] as const,
  extract: (tenderId: string, type?: string) => 
    [...tenderDocsKeys.all, 'extract', { tenderId, type }] as const,
  rules: (type: string) => [...tenderDocsKeys.all, 'rules', type] as const,
  status: (jobId: string) => [...tenderDocsKeys.all, 'status', jobId] as const,
  health: () => [...tenderDocsKeys.all, 'health'] as const,
};

export function useExtractTenderDoc(tenderId: string, type?: string) {
  return useMutation({
    mutationFn: (data: ExtractRequest) => apiFetch<ExtractResponse>('/tender-docs/extract', {
      method: 'POST',
      body: JSON.stringify(data),
    }),
  });
}

export function useDocumentRules(documentType: string) {
  return useQuery({
    queryKey: tenderDocsKeys.rules(documentType),
    queryFn: () => apiFetch<DocumentRulesResponse>(`/tender-docs/rules/${documentType}`),
    staleTime: 60 * 60 * 1000, // 1 hour
  });
}
```

---

## Integration Flow (AgentBrain)

**1. Tender Acquisition Agent (Agent-002)**
```
API: POST /tender/upload (tender_id, documents)
↓
Agent-002.run()
  ├─ Extracts OR passes to KnowledgeAPI (/knowledge/share)
  ├─ Calls DocumentAI /tender-docs/extract (for TDS/BOQ extraction)
  └─ Populates brain with knowledge entries
```

**2. BOQ Brain Compare (Brain API)**
```
API: POST /api/boq/brain-compare (tender_id, sor_agency, zone)
↓
IntelligenceService.query_brain()
  └─ Fetches /knowledge/entry/{tender_id}/boq_text
  └─ Uses /knowledge/entry/{tender_id}/tds_text for financial criteria
```

**3. Document Validation Pipeline**
```
Upload → Extract (TDS + BOQ) → Validate (PPR2025) → Knowledge Storage → AgentBrain Cache
↓                                                                    ↓
/sor/compare                             /knowledge/share
```

---

## Versioning

- `v1`: Current (AgentBrain integration, brain ↔ PostgreSQL sync)
- `v2` (planned): Event-driven real-time extraction, WebSocket progress updates

---

## Configuration Options

Environment variables:
- `DOCUMENT_AI_SYNC_FALLBACK=true|false` (default: false)
- `DOCUMENT_AI_OCR_ENGINE=tesseract|easyocr` (default: tesseract)
- `DOCUMENT_AI_CONFIDENCE_THRESHOLD=0.42` (default: 0.42)
- `DOCUMENT_AI_MAX_FILE_SIZE=52428800` (50MB, default: 10MB)
- `DOCUMENT_AI_MAX_PAGES=100` (default: 50)

---

## Monitoring & Telemetry

**Metrics**:
- Extraction success/failure rates
- Average processing time per document type
- OCR confidence scores
- PDF parsing accuracy
- Memory usage by extraction type

**Alerts**:
- Failed extractions > 5% of total
- Processing time > 2x threshold for document type
- OCR confidence < 0.7 for critical fields

> **Dependency**: `/app/services/pdf_parser.py` → `_parse_bwdb_boq_tables()`, `/app/services/tds_extractor.py` → financial criteria regex extraction