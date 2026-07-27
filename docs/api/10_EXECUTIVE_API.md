# Executive API Contract

**Router**: `/api/v1/executive` (v1) / `/api/v2/executive` (v2 enterprise)  
**Tags**: `executive`  
**Auth**: JWT (tenant-scoped)

---

## Endpoint Catalog

| Method | Path | Purpose | Auth |
|--------|------|---------|------|
| GET | `/executive/overview` | Aggregate executive KPIs (leads, pipeline value, etc.) | JWT |
| GET | `/executive/pipeline` | Live tender pipeline by agency + closing windows | JWT |
| GET | `/executive/agency-spend` | Agency spend analytics by year | JWT |
| GET | `/executive/contractor-heatmap` | Top contractors × agency heatmap | JWT |
| GET | `/executive/report` | Full executive report (ML predictions, SLT, competitor intel) | JWT |

---

## Request/Response Schemas

### `GET /executive/overview`

**Response (200)**
```json
{
  "success": true,
  "data": {
    "total_tenders": 1247,
    "total_awards": 238951,
    "total_npp_records": 108934,
    "total_predictions": 78243,
    "total_contractors": 32156,
    "total_agencies": 12,
    "avg_discount_pct": 12.34,
    "agencies": ["BWDB", "PWD", "LGED", "BPDB", "BPDB_TERRITORY"],
    "model_status": { "trained": true, "last_trained_at": "2026-07-10T14:30:00Z" },
    "model_report": { "accuracy": 0.87, "confidences": { "high": 0.42, "medium": 0.31, "low": 0.27 } },
    "timestamp": "2026-07-21T12:00:00Z"
  }
}
```

### `GET /executive/pipeline`

**Response (200)**
```json
{
  "success": true,
  "total_live_tenders": 1247,
  "estimated_total_pipeline_value_bdt": 48750000000,
  "value_note": "Estimated: live count x agency historical average award (live notices carry no cost estimate)",
  "agencies": [
    {
      "agency_code": "BWDB",
      "live_tenders": 458,
      "closing_7d": 89,
      "closing_14d": 167,
      "closing_30d": 312,
      "avg_historical_award_bdt": 420000,
      "estimated_pipeline_value_bdt": 192360000000
    },
    {
      "agency_code": "PWD",
      "live_tenders": 392,
      "closing_7d": 76,
      "closing_14d": 143,
      "closing_30d": 267,
      "avg_historical_award_bdt": 280000,
      "estimated_pipeline_value_bdt": 109760000000
    }
  ]
}
```

### `GET /executive/agency-spend`

**Query Parameters**
| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `years` | int | 5 | Span (1-15) |

**Response (200)**
```json
{
  "success": true,
  "years": ["2026", "2025", "2024", "2023", "2022"],
  "agencies": [
    {
      "agency_code": "BWDB",
      "years": {
        "2026": { "awards": 458, "spend_bdt": 420000000, "avg_npp": 0.876 },
        "2025": { "awards": 421, "spend_bdt": 392000000, "avg_npp": 0.882 }
      },
      "total_spend_bdt": 812000000,
      "total_awards": 879
    }
  ]
}
```

### `GET /executive/contractor-heatmap`

**Query Parameters**
| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `top_n` | int | 20 | Top contractors to show (5-50) |

**Response (200)**
```json
{
  "success": true,
  "contractors": [
    { "name": "Skyatech Ltd", "total_wins": 847, "total_value_bdt": 12458000000 },
    { "name": "BuildRight Asia", "total_wins": 623, "total_value_bdt": 9870000000 }
  ],
  "agencies": ["BWDB", "PWD", "LGED", "BPDB"],
  "cells": [
    {
      "contractor": "Skyatech Ltd",
      "agency_code": "BWDB",
      "wins": 247,
      "value_bdt": 4250000000,
      "avg_npp": 0.876
    }
  ]
}
```

### `GET /executive/report`

**Query Parameters**
| Param | Type | Description |
|-------|------|-------------|
| `tender_id` | string | Optional: executive narrative for a single tender |

**Response (200)** - Large report object (see AGENTS_ENTRY.md for full structure) with:
- Bid suggestion (Bidding Recommended / Proceed with Caution / Do Not Bid)
- Win probability (ML model vs heuristic) with confidence
- Executive KPI widgets (SLT, Competitor intel, Market rate deviation)
- Action items (BOQ status, document checks, agent tasks)

---

## Error Schema

```json
{
  "detail": "Invalid agency_code 'XYZ'",
  "status_code": 400,
  "error_code": "EXECUTIVE_VALIDATION_ERROR"
}
```

---

## Permission Requirements

**Core executive role**: `owner` or `admin` for `/agency-spend` and `/contractor-heatmap`
**Read access**: `viewer` or higher for `/overview`, `/pipeline`
**Full access**: `estimator`, `compliance`, `admin`, `owner` for `/report`

---

## Rate Limits

| Endpoint | Limit | Window |
|----------|-------|--------|
| `/overview` | 30 | 60 |
| `/pipeline` | 30 | 60 |
| `/agency-spend` | 10 | 60 |
| `/contractor-heatmap` | 15 | 60 |
| `/report` | 5 | 60 |

---

## Caching

- `GET /overview`: `private, max-age=60` (business metrics change daily)
- `GET /pipeline`: `private, max-age=30` (new tenders appear periodically)
- `GET /agency-spend`: `private, max-age=300` (historical spans)
- `GET /contractor-heatmap`: `private, max-age=60` (contractor win streaks)
- `GET /report`: `private, max-age=60` (ML model may update)

---

## React Query Mapping

```typescript
export const execKeys = {
  all: () => ['executive'] as const,
  overview: () => [...execKeys.all, 'overview'] as const,
  pipeline: () => [...execKeys.all, 'pipeline'] as const,
  spend: (years: number) => [...execKeys.all, 'spend', { years }] as const,
  heatmap: (topN: number) => [...execKeys.all, 'heatmap', { topN }] as const,
  report: (tenderId?: string) => [...execKeys.all, 'report', { tenderId }] as const,
};

export function useExecutiveOverview() {
  return useQuery({
    queryKey: execKeys.overview(),
    queryFn: () => apiFetch<ExecutiveOverviewResponse>('/executive/overview'),
    staleTime: 60_000,
  });
}

export function useExecutivePipeline() {
  return useQuery({
    queryKey: execKeys.pipeline(),
    queryFn: () => apiFetch<ExecutivePipelineResponse>('/executive/pipeline'),
    staleTime: 30_000,
  });
}
```

---

## Zustand Store

```typescript
// stores/executive.ts
interface ExecutiveState {
  overview: ExecutiveOverview | null;
  pipeline: ExecutivePipeline | null;
  report: ExecutiveReport | null;
  setOverview: (d: ExecutiveOverview) => void;
  setPipeline: (d: ExecutivePipeline) => void;
  setReport: (d: ExecutiveReport) => void;
  clear: () => void;
}
```

---

## Agent Integration

- **ML Prediction**: Uses `/api/v1/ppr2025/predict` endpoint (Agent-009)
- **SLT Intelligence**: Uses `/api/v1/ppr2025/evaluate/slt` (Agent-009)
- **Competitor Intelligence**: Uses `agent-013-competitor-intelligence` (via `/api/agents/{agent_id}/run`)
- **Bid Suggestion Logic**: Custom executive rules + ML hybrid (see executive.py:430-460)

---

## Versioning

- `v1`: Current (PostgreSQL-based intelligence queries, ML caching)
- `v2` (planned): Real-time WebSocket push for `/pipeline` updates