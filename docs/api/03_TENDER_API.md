# Tender API Contract

**Router**: `/api/v1/tender`  
**Tags**: `tenders`  
**Auth**: Optional JWT (tenant-scoped if authenticated)

---

## Endpoint Catalog

| Method | Path | Purpose | Auth |
|--------|------|---------|------|
| POST | `/tender/upload` | Upload tender bundle (notice, TDS, BOQ, SOR, templates) | Optional |
| GET | `/tender/list` | List tenders from filesystem manager | Optional |
| GET | `/tender/{tender_id}` | Get tender details + extracted variables | Optional |
| POST | `/tender/{tender_id}/extract` | Re-extract variables from documents | Optional |
| DELETE | `/tender/{tender_id}` | Delete tender and documents | Optional |
| GET | `/tender/{tender_id}/document/{doc_type}` | Download specific document | Optional |
| POST | `/tender/scan-uploads` | Scan uploads folder, organize tenders | Optional |
| GET | `/tender/{tender_id}/bundle` | Download tender bundle ZIP | Optional |
| POST | `/tender/db` | Create tender in database | Optional |
| GET | `/tender/db` | List tenders from database (paginated) | Optional |
| GET | `/tender/db/{tender_id}` | Get tender from database | Optional |

---

## Request/Response Schemas

### `POST /tender/upload`

**Content-Type**: `multipart/form-data`

**Form Fields**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `notice` | file | No | NIT PDF |
| `tds` | file | No | TDS PDF |
| `tds_2` | file | No | Additional TDS |
| `boq` | file | No | BOQ PDF/Excel |
| `sor` | file | No | SOR reference |
| `docx_templates` | file[] | No | DOCX templates |
| `xlsx_templates` | file[] | No | XLSX templates |
| `tender_id` | string | Query | Optional tender ID |
| `sor_agency` | string | Query | BWDB/PWD/LGED (default BWDB) |
| `zone` | string | Query | A/B/C/D |

**Response (200)**
```json
{
  "success": true,
  "tender_id": "1290886",
  "documents": {
    "notice": "notice.pdf",
    "tds": "tds.pdf",
    "boq": "boq.pdf",
    "sor": "sor.pdf"
  },
  "extracted": {
    "title": "Construction of Bridge",
    "procuring_entity": "BWDB Dhaka Division",
    "estimated_cost": 45000000,
    "tender_security": 450000,
    "package_no": "BWDB-DHA-01/2024-25",
    "closing_date": "2026-08-15"
  },
  "comparison": { ... },
  "bundle_zip": "uploads/1290886_bundle.zip"
}
```

**Note**: Also persists to DB (Tender + TenderDocument records).

---

### `GET /tender/list`

**Query**
| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `limit` | int | 50 | Max results (1-200) |
| `offset` | int | 0 | Pagination offset |

**Response (200)**
```json
{
  "success": true,
  "total": 1247,
  "limit": 50,
  "offset": 0,
  "tenders": [
    {
      "tender_id": "1290886",
      "title": "Construction of Bridge",
      "procuring_entity": "BWDB Dhaka Division",
      "estimated_cost": 45000000,
      "status": "ACTIVE",
      "documents": ["notice", "tds", "boq"],
      "created_at": "2026-07-15T10:30:00Z"
    }
  ]
}
```

---

### `GET /tender/{tender_id}`

**Response (200)**
```json
{
  "success": true,
  "tender_id": "1290886",
  "documents": {
    "notice": "notice.pdf",
    "tds": "tds.pdf",
    "boq": "boq.pdf"
  },
  "variables": {
    "title": "Construction of Bridge",
    "procuring_entity": "BWDB Dhaka Division",
    "estimated_cost": 45000000,
    "tender_security": 450000,
    "package_no": "BWDB-DHA-01/2024-25",
    "closing_date": "2026-08-15",
    "contact_person": "Eng. Ahmed",
    "contact_phone": "+8801712345678"
  }
}
```

---

### `POST /tender/{tender_id}/extract`

**Response (200)**
```json
{
  "success": true,
  "tender_id": "1290886",
  "extracted": { ... }
}
```

---

### `DELETE /tender/{tender_id}`

**Response (200)**
```json
{ "success": true }
```

---

### `GET /tender/{tender_id}/document/{doc_type}`

**Path Params**
- `doc_type`: `notice|tds|tds_2|boq|sor`

**Response**: File download (PDF/Excel)

---

### `POST /tender/scan-uploads`

**Response (200)**
```json
{
  "success": true,
  "tenders_created": 12,
  "tenders_updated": 3,
  "details": { ... }
}
```

---

### `GET /tender/{tender_id}/bundle`

**Response**: ZIP file download (`application/zip`)

---

### `POST /tender/db`

**Request**
```json
{
  "tender_id": "1290886",
  "title": "Construction of Bridge",
  "procuring_entity": "BWDB Dhaka Division",
  "estimated_cost": 45000000,
  "tender_security": 450000,
  "status": "ACTIVE",
  "sor_agency": "BWDB",
  "zone": "A"
}
```

**Response (201)**: `TenderRead` schema

---

### `GET /tender/db`

**Query**
| Param | Type | Default |
|-------|------|---------|
| `skip` | int | 0 |
| `limit` | int | 20 (max 200) |

**Response (200)**: `TenderRead[]`

---

### `GET /tender/db/{tender_id}`

**Response (200)**: `TenderRead` or 404

---

## Error Codes

| Code | HTTP | Scenario |
|------|------|----------|
| `NO_FILES` | 400 | No files uploaded to `/upload` |
| `TENDER_NOT_FOUND` | 404 | Tender ID not in FS or DB |
| `DOC_NOT_FOUND` | 404 | Requested document type missing |
| `INVALID_TENDER_ID` | 400 | Path traversal attempt in bundle download |

---

## Permission Requirements

| Endpoint | Role | Notes |
|----------|------|-------|
| All | `viewer` or guest | Tenant-scoped in DB mode |

---

## Rate Limits

| Endpoint | Limit | Window |
|----------|-------|--------|
| `/upload` | 10 | 60 sec |
| `/list`, `/db` | 60 | 60 sec |
| `/scan-uploads` | 5 | 300 sec |
| `/bundle` | 20 | 60 sec |

---

## Caching

| Endpoint | Cache-Control |
|----------|---------------|
| `/list`, `/db` | `private, max-age=30` |
| `/{id}` | `private, max-age=60` |
| `/bundle` | `no-cache` (streaming) |

---

## React Query Mapping

```typescript
// hooks/useTenders.ts
export const tenderKeys = {
  all: ['tenders'] as const,
  list: (params: ListParams) => [...tenderKeys.all, 'list', params] as const,
  detail: (id: string) => [...tenderKeys.all, 'detail', id] as const,
  bundle: (id: string) => [...tenderKeys.all, 'bundle', id] as const,
};

export function useTenderList(params: ListParams) {
  return useQuery({
    queryKey: tenderKeys.list(params),
    queryFn: () => apiFetch<TenderListResponse>('/tender/list', { params }),
    staleTime: 30_000,
  });
}

export function useUploadTender() {
  return useMutation({
    mutationFn: (formData: FormData) => apiFetch('/tender/upload', {
      method: 'POST',
      body: formData,
      headers: {}, // Let browser set multipart boundary
    }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: tenderKeys.all }),
  });
}
```

---

## Zustand Store

```typescript
// stores/tender.ts
interface TenderState {
  currentTender: TenderDetail | null;
  uploadProgress: number;
  setCurrentTender: (t: TenderDetail) => void;
  setUploadProgress: (p: number) => void;
}
```

---

## Versioning

- `v1`: Current (FS + DB dual mode)
- `v2` (planned): Unified DB-only with S3/MinIO object storage