# Competitor API Contract

**Router**: `/api/v1/competitors`  
**Tags**: `competitors`  
**Auth**: JWT (tenant-scoped)

---

## Overview

Competitor Intelligence API for **contractor analysis**, **bid positioning**, and **market intelligence** in the construction procurement workflow. Core to **competitor analysis**, **win probability prediction**, and **capacity planning**. Provides access to **contractor performance data**, **bid patterns**, and **market trends**.

**Primary Use Cases**:
- Analyze competitor track record and financial capacity
- Benchmark bids against market rates
- Identify competitor strengths/weaknesses
- Predict win probabilities for tender bids
- Generate competitive intelligence reports

---

## Endpoint Catalog

| Method | Path | Purpose | Auth |
|--------|------|---------|------|
| GET | `/competitors` | List competitors with filters | JWT |
| GET | `/competitors/{identifier}` | Get competitor profile by ID | JWT |
| GET | `/competitors/{identifier}/capacity` | Contractor capacity analysis | JWT |
| GET | `/competitors/{identifier}/finance` | Contractor financial analysis | JWT |
| GET | `/competitors/stats` | Competitor market statistics | JWT |

---

## Request/Response Schemas

### `GET /competitors`

**Query Parameters**
| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `district` | string | null | Filter by district |
| `category` | string | null | Filter by agency (BWDB/PWD/LGED) |
| `search` | string | null | Text search in company name |
| `skip` | int | 0 | Pagination offset |
| `limit` | int | 50 | Max results (1-500) |

**Response (200)**
```json
{
  "success": true,
  "total": 1247,
  "limit": 50,
  "offset": 0,
  "competitors": [
    {
      "id": "contractor-12345",
      "name": "Skyatech Ltd",
      "normalized_name": "skyatech ltd",
      "license_number": "123456789",
      "address": "123 Main Road, Dhaka",
      "district": "Dhaka",
      "division": "Dhaka Division",
      "contact_person": "John Smith",
      "phone": "+8801712345678",
      "email": "contact@skyatech.com",
      "website": "https://skyatech.com",
      "entity_type": "Company",
      "category": "BWDB",
      "specializations": {
        "earthwork": 0.85,
        "concrete": 0.72,
        "steel_structure": 0.68
      },
      "total_awards": 847,
      "total_awarded_amount": 12458000000,
      "avg_discount_pct": 3.45,
      "avg_project_size": 45000000,
      "first_award_date": "2020-01-15T10:00:00Z",
      "last_award_date": "2026-06-20T14:30:00Z",
      "active_districts": {"Dhaka": 15, "Chittagong": 8},
      "work_types": {},
      "predicted_win_probability": 0.71,
      "predicted_price_range": {"min": 45000000, "max": 55000000},
      "created_at": "2026-01-15T10:00:00Z",
      "updated_at": "2026-07-21T10:00:00Z"
    }
  ]
}
```

### `GET /competitors/{identifier}`

**Path Params**
- `identifier`: `contractor-12345` or `Skyatech` (name search)

**Response (200)** — Full profile with DNA:
```json
{
  "success": true,
  "contractor": {
    "id": "contractor-12345",
    "name": "Skyatech Ltd",
    "normalized_name": "skyatech ltd",
    "license_number": "123456789",
    "address": "123 Main Road, Dhaka",
    "district": "Dhaka",
    "division": "Dhaka Division",
    "contact_person": "John Smith",
    "phone": "+8801712345678",
    "email": "contact@skyatech.com",
    "website": "https://skyatech.com",
    "entity_type": "Company",
    "category": "BWDB",
    "specializations": { ... },
    "total_awards": 847,
    "total_awarded_amount": 12458000000,
    "avg_discount_pct": 3.45,
    "avg_project_size": 45000000,
    "first_award_date": "2020-01-15T10:00:00Z",
    "last_award_date": "2026-06-20T14:30:00Z",
    "active_districts": {"Dhaka": 15, "Chittagong": 8}
  },
  "dna": {
    "contractor_id": "contractor-12345",
    "contractor_name": "Skyatech Ltd",
    "total_wins": 847,
    "total_amount_bdt": 12458000000,
    "avg_award_amount_bdt": 14688000,
    "agency_affinity": {"BWDB": 0.89, "PWD": 0.23, "LGED": 0.12},
    "zone_affinity": {"Dhaka": 0.85, "Chittagong": 0.61, "Sylhet": 0.43},
    "win_rate": 0.72,
    "avg_rank": 1.2,
    "responsive_rate": 0.94,
    "slt_rate": 0.87,
    "health_score": 0.88
  }
}
```

### `GET /competitors/{identifier}/capacity`

**Query Parameters**
| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `tender_value_bdt` | float | 0.0 | Value of the tender you're considering |

**Response (200)**
```json
{
  "success": true,
  "contractor": "Skyatech Ltd",
  "canonical_contractor_id": "contractor-12345",
  "total_contracts": 847,
  "total_amount_bdt": 12458000000,
  "last_5yr_awarded_amount_bdt": 3492000000,
  "work_in_hand_bdt": 850000000,
  "estimated_turnover_bdt": 18200000000,
  "avg_award_bdt": 14688000,
  "tender_capacity_bdt": 19500000000,
  "tender_value_bdt": 50000000,
  "utilization_ratio": 0.00026,
  "capacity_status": "available",
  "agencies_worked": ["BWDB", "PWD", "LGED"],
  "districts_worked": ["Dhaka", "Chittagong"],
  "work_type_mix": {"earthwork": 0.68, "concrete": 0.72},
  "is_joint_venture": false,
  "jv_member_count": 0,
  "data_confidence_score": 0.88,
  "source": "contractor_dna_v2"
}
```

### `GET /competitors/{identifier}/finance`

**Response (200)**
```json
{
  "success": true,
  "contractor": "Skyatech Ltd",
  "canonical_contractor_id": "contractor-12345",
  "total_contracts": 847,
  "total_amount_bdt": 12458000000,
  "last_5yr_awarded_amount_bdt": 3492000000,
  "work_in_hand_bdt": 850000000,
  "estimated_turnover_bdt": 18200000000,
  "tender_capacity_bdt": 19500000000,
  "avg_award_bdt": 14688000,
  "avg_npp": 0.876,
  "avg_discount_pct": 3.45,
  "win_rate": 0.72,
  "total_bids": 1247,
  "health_score": 0.88,
  "reliability_score": 0.85,
  "data_confidence_score": 0.88,
  "completion_rate": 0.91,
  "on_time_rate": 0.88,
  "avg_delay_days": 3.2,
  "estimated_liquidity_band_bdt": {
    "low": 1468800.00,
    "high": 4687500.00
  },
  "work_type_mix": {"earthwork": 0.68, "concrete": 0.72},
  "is_joint_venture": false,
  "jv_member_count": 0,
  "source": "contractor_dna_v2"
}
```

### `GET /competitors/stats`

**Response (200)**
```json
{
  "success": true,
  "total_competitors": 32156,
  "total_awarded_amount": 1247500000000,
  "total_awards": 238451,
  "source": "contractor_dna_v2",
  "by_category": [
    {"category": "BWDB", "count": 12047, "total_amount": 723450000000},
    {"category": "PWD", "count": 8923, "total_amount": 456780000000},
    {"category": "LGED", "count": 5186, "total_amount": 278700000000}
  ],
  "by_district": [
    {"district": "Dhaka", "count": 8947, "total_amount": 567890000000},
    {"district": "Chittagong", "count": 6124, "total_amount": 342560000000},
    {"district": "Sylhet", "count": 4085, "total_amount": 198750000000}
  ]
}
```

---

## Error Codes

| Code | HTTP | Scenario |
|------|------|----------|
| `COMPETITOR_NOT_FOUND` | 404 | Contractor not found |
| `COMPETITOR_SEARCH_FAILED` | 500 | Search engine error |

---

## Permission Requirements

| Endpoint | Role | Notes |
|----------|------|-------|
| `/competitors` | `viewer` or higher | Read competitor list |
| `/competitors/{id}` | `viewer` or higher | Read full profile |
| `/competitors/{id}/capacity` | `viewer` or higher | Capacity analysis |
| `/competitors/{id}/finance` | `viewer` or higher | Financial details |

---

## Rate Limits

| Endpoint | Limit |
|----------|-------|
| `/competitors` | 60/min |
| `/competitors/{id}` | 60/min |
| `/competitors/{id}/capacity` | 30/min |
| `/competitors/{id}/finance` | 30/min |
| `/competitors/stats` | 30/min |

---

## Caching

- `GET /competitors`: `private, max-age=300` (contractor profiles change slowly)
- `GET /competitors/stats`: `private, max-age=1800` (hourly updates)
- Other: `private, max-age=60`

---

## React Query Mapping

```typescript
export const competitorKeys = {
  all: () => ['competitors'] as const,
  list: (params: CompetitorsListParams) => 
    [...competitorKeys.all, 'list', params] as const,
  detail: (id: string) => [...competitorKeys.all, 'detail', id] as const,
  capacity: (id: string, params?: CapacityParams) => 
    [...competitorKeys.all, 'capacity', id, { params }] as const,
  finance: (id: string) => [...competitorKeys.all, 'finance', id] as const,
  stats: () => [...competitorKeys.all, 'stats'] as const,
};

export function useCompetitors(params: CompetitorsListParams) {
  return useQuery({
    queryKey: competitorKeys.list(params),
    queryFn: () => apiFetch<CompetitorsListResponse>('/competitors', { params }),
    staleTime: 60_000,
  });
}

export function useCompetitorProfile(id: string) {
  return useQuery({
    queryKey: competitorKeys.detail(id),
    queryFn: () => apiFetch<CompetitorProfileResponse>(`/competitors/${id}`),
    staleTime: 300_000,
  });
}
```

---

## Integration Points

### Bid Position Optimization
```
GET /competitors/{id}/capacity → Contractor capacity → 
  POST /api/v1/pricing/estimate → Pricing analysis → 
    POST /api/v1/competitors/{id}/benchmark?agency=BWDB&zone=A → Win probability calculation
```

### Market Intelligence Dashboard
```
GET /competitors/stats → Market trends → 
  GET /api/v1/intelligence/lifecycle/stats → Award patterns → 
    GET /api/v1/executive/overview → Executive KPIs
```

### Tender Qualification
```
GET /competitors/{id}/finance → Financial screening → 
  Validate against PPR2025 criteria → 
    Decision: Qualify/Suspend/Reject
```

---

## Versioning

- `v1`: Current (PostgreSQL contractor profiles)
- `v2` (planned): GraphQL queries, real-time market data

---

## Configuration Options

Environment variables:
- `COMPETITOR_DATA_SOURCE=contractor_dna|award_records` (default: contractor_dna)
- `COMPETITOR_SEARCH_LIMIT=1000` (default: 500)
- `COMPETITOR_CACHE_TTL=600` (seconds)
- `COMPETITOR_SPECIALIZATION_THRESHOLD=0.5` (weight for specializations)

---

## Monitoring & Telemetry

**Metrics**:
- Search queries and results
- Profile view statistics
- Comparison operations
- API latency

**Alerts**:
- Search failures > 5%
- Profile data freshness

> **Dependency**: `app/models/competitor.py` → `ContractorProfile`, `CompetitorAward`
> **Integration**: `app/services/job_service.py` → Competitor DNA loading from multiple sources
> **Queue**: `workers/tasks/competitor_tasks.py` → Benchmark calculations, profile updates

---

## OpenAPI Reference

See `/openapi.json#/paths/~1api~1competitors~1GET`