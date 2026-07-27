# BOQ API Contract

**Router**: `/api/v1/boq`  
**Tags**: `boq`  
**Auth**: Optional JWT (tenant-scoped jobs)

---

## Endpoint Catalog

| Method | Path | Purpose | Auth |
|--------|------|---------|------|
| POST | `/boq/compare` | Compare BOQ vs SOR (async job) | Optional |
| POST | `/boq/brain-compare` | Compare using brain knowledge (async) | Optional |
| GET | `/boq/jobs/{job_id}` | Poll job status | Optional |
| GET | `/boq/jobs/{job_id}/result` | Get completed comparison result | Optional |
| POST | `/boq/upload` | Upload BOQ file (PDF/Excel/Word) | Optional |
| GET | `/boq/export/{file_id}` | Export comparison (xlsx/docx) | Optional |
| GET | `/boq/latest` | Latest comparison for dashboard | Optional |
| GET | `/boq/history` | User's comparison history (paginated) | JWT |
| GET | `/boq/{comparison_id}` | Specific comparison detail | JWT |

---

## Request/Response Schemas

### `POST /boq/compare`

**Request** (multipart/form-data)
```
boq_file_id: "abc123def"     (from /boq/upload)
sor_agency: "BWDB|PWD|LGED"  (default: BWDB)
zone: "A|B|C|D"              (optional, JSON or string)
tender_info: '{"tender_id":"1298004","package_no":"BWDB-CTG-01","estimated_cost_app":45500000}' (optional JSON)
```

**Response (202)**
```json
{
  "job_id": "uuid",
  "status": "PENDING",
  "status_url": "/api/v1/boq/jobs/uuid"
}
```

**Sync Fallback** (if `BOQ_SYNC_FALLBACK=true`): Returns full comparison result directly (200)

---

### `POST /boq/brain-compare`

**Request** (multipart/form-data)
```
tender_id: "1298004"
sor_agency: "BWDB"
zone: "A"
```

**Response (202)**
```json
{
  "job_id": "uuid",
  "status": "PENDING",
  "status_url": "/api/v1/boq/jobs/uuid"
}
```

**Prerequisites**: Brain must have `tender_document` + `boq_text` knowledge entries for `tender_id`

---

### `GET /boq/jobs/{job_id}`

**Response (200)**
```json
{
  "job_id": "uuid",
  "kind": "compare|brain_compare",
  "status": "PENDING|RUNNING|SUCCESS|FAILED",
  "progress": 0-100,
  "error": "error message if failed",
  "comparison_id": "uuid (when SUCCESS)",
  "result_url": "/api/v1/boq/jobs/uuid/result (when SUCCESS)",
  "created_at": "2026-07-21T10:00:00Z",
  "updated_at": "2026-07-21T10:02:30Z"
}
```

---

### `GET /boq/jobs/{job_id}/result`

**Response (200) — Full Comparison Payload**
```json
{
  "success": true,
  "tender_id": "1298004",
  "boq_file_id": "abc123def",
  "sor_agency": "BWDB",
  "zone": "B",
  "data": [
    {
      "item_no": "1",
      "code": "40-200-00",
      "agency": "BWDB",
      "work_type": "Earthwork",
      "desc": "Excavation in all kinds of soil",
      "unit": "m3",
      "qty": 5000,
      "rate": 185.50,
      "sor_rate": 192.00,
      "sor_source": "40-200-00",
      "diff": -6.50,
      "pct_diff": -3.39,
      "flag": "BELOW_SOR",
      "section": "Section 6 - BOQ"
    }
  ],
  "summary": {
    "by_work_type": [
      { "work_type": "Earthwork", "items": 15, "total_sor": 960000, "total_quoted": 927500 }
    ],
    "total_sor": 45500000,
    "total_quoted": 43800000,
    "discount_pct": 3.74
  },
  "flagged": [...],
  "variances": 12,
  "mismatches": 3,
  "matches": 45,
  "below_sor": 8,
  "excel_url": "https://minio/.../comparison_abc123.xlsx",
  "docx_url": "https://minio/.../comparison_abc123.docx",
  "financial_check": [
    { "criteria": "Average Annual Turnover", "required": 5500000, "status": "PASS" }
  ],
  "estimated_cost_app": 45500000
}
```

**Errors**
- `404` Job not found / not owned by tenant
- `409` Job not yet complete (`{ job_id, status, error }`)

---

### `POST /boq/upload`

**Request** (multipart/form-data)
```
file: <binary> (pdf|xlsx|xls|docx|doc|txt)
file_type: "boq" (default)
```

**Response (200)**
```json
{
  "success": true,
  "file_id": "a1b2c3d4",
  "filename": "boq_tender_1298004.pdf",
  "file_type": "pdf",
  "size_bytes": 2048576,
  "object_key": "uploads/a1b2c3d4.pdf"
}
```

**Errors**
- `413` File > 50MB (config: `MAX_FILE_SIZE`)
- `415` Unsupported extension
- `500` Storage write failure

---

### `GET /boq/export/{file_id}?format=xlsx|docx`

**Response**: File download (307 redirect to presigned MinIO URL or local FileResponse)

**Errors**
- `404` Comparison not found / artifact missing

---

### `GET /boq/latest`

**Response (200)** — Same shape as job result, plus:
```json
{
  "comparison_id": "uuid",
  "boq_file_id": "abc123def",
  "created_at": "2026-07-21T10:02:30Z"
}
```

---

### `GET /boq/history?skip=0&limit=20`

**Response (200)**
```json
[
  {
    "id": "uuid",
    "boq_file_id": "abc123def",
    "sor_agency": "BWDB",
    "zone": "B",
    "total_items": 60,
    "matches": 45,
    "variances": 12,
    "mismatches": 3,
    "discount_pct": 3.74,
    "total_sor_amount": 45500000,
    "total_quoted_amount": 43800000,
    "created_at": "2026-07-21T10:02:30Z"
  }
]
```

---

### `GET /boq/{comparison_id}`

**Response (200)** — Single `BOQComparisonRead` (same as history item)

---

## Error Schema

```json
{
  "detail": "BOQ file abc123def not found",
  "status_code": 404,
  "error_code": "BOQ_FILE_NOT_FOUND"
}
```

**Common codes**:
- `BOQ_FILE_NOT_FOUND`
- `BOQ_JOB_NOT_FOUND`
- `BOQ_JOB_NOT_READY`
- `BOQ_COMPARISON_FAILED`
- `SOR_AGENCY_INVALID`
- `ZONE_INVALID`

---

## Permission Requirements

| Endpoint | Auth | Tenant Scope |
|----------|------|--------------|
| `/compare`, `/brain-compare` | Optional | Job owned by resolved user |
| `/jobs/*` | Optional | Job owned by resolved user |
| `/upload` | Optional | N/A (file staged) |
| `/export` | Optional | Comparison accessible |
| `/latest` | Optional | Latest for resolved user |
| `/history`, `/{id}` | **Required (JWT)** | User's own comparisons |

> **Note**: `get_optional_user` resolves guest → system owner user. Multi-tenant isolation via `resolve_owner_user_id()`.

---

## Rate Limits

| Endpoint | Limit |
|----------|-------|
| `/compare`, `/brain-compare` | 10/min |
| `/jobs/*` (polling) | 60/min |
| `/upload` | 20/min |
| `/history` | 30/min |

---

## Caching

- `GET /jobs/{id}`: `private, max-age=5, stale-while-revalidate=30`
- `GET /jobs/{id}/result`: `private, max-age=300` (ETag on comparison version)
- `GET /latest`: `private, max-age=60`
- `GET /history`: `private, max-age=30`

---

## React Query Mapping

```typescript
// hooks/useBoq.ts
export const boqKeys = {
  all: ['boq'] as const,
  jobs: (jobId: string) => [...boqKeys.all, 'job', jobId] as const,
  jobResult: (jobId: string) => [...boqKeys.all, 'job', jobId, 'result'] as const,
  latest: () => [...boqKeys.all, 'latest'] as const,
  history: (skip: number, limit: number) => [...boqKeys.all, 'history', { skip, limit }] as const,
  detail: (id: string) => [...boqKeys.all, 'detail', id] as const,
};

// Polling job status
export function useBoqJob(jobId: string) {
  return useQuery({
    queryKey: boqKeys.jobs(jobId),
    queryFn: () => apiFetch<BoqJobStatus>(`/boq/jobs/${jobId}`),
    refetchInterval: (data) => data?.status === 'SUCCESS' ? false : 3000,
    enabled: !!jobId,
  });
}

// Compare mutation
export function useCompareBoq() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (params: CompareParams) => apiFetch<JobResponse>('/boq/compare', {
      method: 'POST',
      body: JSON.stringify(params),
    }),
    onSuccess: (data) => {
      // Start polling
      queryClient.invalidateQueries({ queryKey: boqKeys.jobs(data.job_id) });
    },
  });
}
```

---

## Zustand Store

```typescript
// stores/boq.ts
interface BoqState {
  currentJobId: string | null;
  comparisonResult: ComparisonResult | null;
  setCurrentJob: (id: string) => void;
  setResult: (r: ComparisonResult) => void;
  clear: () => void;
}
```

---

## Async Flow (ADR-004)

```
POST /boq/compare
  → 202 { job_id }
  → Celery worker: run_boq_compare_job(job_id)
      → BOQProcessor.compare()
      → Persist BOQComparison + BOQItems
      → Generate Excel/DOCX → MinIO
      → Update BOQJob: status=SUCCESS, comparison_id, result_meta
  → Client polls GET /boq/jobs/{job_id}
  → On SUCCESS: GET /boq/jobs/{job_id}/result
```

---

## Versioning

- `v1`: Current (async jobs, Celery, MinIO artifacts)
- `v2` (planned): WebSocket progress, chunked BOQ processing, real-time diff preview