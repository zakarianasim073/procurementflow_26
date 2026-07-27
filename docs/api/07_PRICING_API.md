# Pricing API Contract

**Router**: `/api/v1/pricing`  
**Tags**: `pricing`  
**Auth**: JWT (tenant-scoped)

---

## Overview

Pricing API for **bid estimation**, **rate analysis**, and **competitor intelligence** in the construction tender workflow. Core to **pricing optimization**, **win probability prediction**, and **executive decision support**. Provides access to **SOR-backed pricing**, **market rates**, and **competitor benchmarks**.

**Primary Use Cases**:
- Estimate project costs using SOR rates
- Analyze pricing gaps and competitiveness
- Benchmark against market rates
- Optimize bid positioning for win probability
- Generate pricing reports for tender preparation

---

## Endpoint Catalog

| Method | Path | Purpose | Auth |
|--------|------|---------|------|
| POST | `/pricing/estimate` | Estimate bid price using BOQ + SOR | JWT |
| GET | `/pricing/estimate` | Single-item pricing estimate | JWT |
| POST | `/pricing/rate-analysis/from-compare` | Run BOQ comparison + element-level rate analysis | JWT |
| POST | `/pricing/rate-analysis/analyze-items` | Analyze custom list of BOQ items | JWT |
| GET | `/pricing/market-prices` | Get current market prices by zone | JWT |
| GET | `/pricing/compositions` | List available rate analysis compositions | Public |

---

## Request/Response Schemas

### `POST /pricing/estimate`

**Request**
```json
{
  "items": [
    {
      "code": "40-200-00",
      "description": "Excavation in all kinds of soil",
      "unit": "m3",
      "quantity": 5000,
      "agency": "BWDB",
      "zone": "A"
    },
    {
      "code": "26.50.1",
      "description": "Concrete works",
      "unit": "m3",
      "quantity": 500,
      "agency": "PWD"
    }
  ],
  "agency": "BWDB",
  "zone": "A"
}
```

**Response (200)**
```json
{
  "success": true,
  "items": [
    {
      "code": "40-200-00",
      "description": "Excavation in all kinds of soil",
      "unit": "m3",
      "quantity": 5000,
      "agency": "BWDB",
      "zone": "A",
      "rate": 192.00,
      "amount": 960000.0,
      "sor_code": "40-200-00",
      "sor_description": "Excavation in all kinds of soil",
      "confidence": 1.0,
      "matched": true
    }
  ],
  "total_items": 2,
  "matched_items": 1,
  "unmatched_items": 1,
  "estimated_total": 960000.0,
  "source": "sor_service_csv_indexed",
  "processing_time_ms": 1250,
  "sor_used": true,
  "fuzzy_matches": [
    {
      "item_description": "Concrete works",
      "matched_code": "26.50.1",
      "confidence": 0.87
    }
  ]
}
```

### `GET /pricing/estimate`

**Query Parameters**
| Param | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `code` | string | No | — | Item code (optional, use description) |
| `description` | string | No | — | Item description (fallback) |
| `unit` | string | No | — | Item unit of measure |
| `quantity` | number | No | 1.0 | Quantity |
| `agency` | string | No | BWDB | SOR agency |
| `zone` | string | No | A | SOR zone |

**Response (200) — Same shape as POST, single item**

### `POST /pricing/rate-analysis/from-compare`

**Request** (same as `/api/v1/boq/compare` for BOQ file)
```json
{
  "boq_file_id": "abc123def",
  "sor_agency": "BWDB",
  "zone": "A",
  "tender_info": {
    "tender_id": "1298004",
    "package_no": "BWDB-CTG-01/2024-25",
    "estimated_cost_app": 45500000
  }
}
```

**Response (200)** - Comprehensive rate analysis result
```json
{
  "success": true,
  "tender_id": "1298004",
  "zone": "A",
  "comparison": {
    "total_items": 60,
    "total_sor": 45500000,
    "total_quoted": 43800000,
    "discount_pct": 3.74,
    "flagged_items": 12
  },
  "rate_analysis": {
    "items_with_composition": 48,
    "items_without_composition": 12,
    "profit_summary": {
      "items_with_composition": 48,
      "items_total": 60,
      "profit_margins": {
        "avg_pct": 12.5,
        "min_pct": 2.1,
        "max_pct": 28.7,
        "safe_gt_15": 28,
        "tight_5_to_15": 12,
        "at_risk_0_to_5": 3,
        "loss_le_0": 1
      }
    }
  },
  "excel_path": "/runtime/rate_analysis/BOQ_6Tab_RateAnalysis_1298004.xlsx",
  "details": [
    {
      "sor_code": "40-200-00",
      "description": "Excavation in all kinds of soil",
      "quoted_rate": 185.50,
      "sor_rate": 192.00,
      "market_cost_per_unit": 188.75,
      "profit_margin_pct": 4.25,
      "sor_vs_market_pct": -3.44,
      "bid_vs_sor_pct": -3.63,
      "elements_count": 3,
      "elements": [...],
      "coverage_pct": 95.0,
      "summary": "Standard earthwork excavation"
    }
  ]
}
```

### `POST /pricing/rate-analysis/analyze-items`

**Request**
```json
{
  "items": [
    {
      "item_no": "1",
      "code": "40-200-00",
      "description": "Excavation in all kinds of soil",
      "unit": "m3",
      "quantity": 1000,
      "quoted_rate": 185.50,
      "sor_rate": 192.00,
      "work_type": "Earthwork"
    }
  ],
  "zone": "A"
}
```

**Response (200)
```json
{
  "success": true,
  "zone": "A",
  "items_analyzed": 1,
  "results": [
    {
      "sor_code": "40-200-00",
      "description": "Excavation in all kinds of soil",
      "has_composition": true,
      "total_market_cost_per_unit": 188.75,
      "profit_margin_vs_market_pct": 4.25,
      "sor_vs_market_pct": -3.44,
      "bid_vs_sor_pct": -3.63,
      "elements_count": 3,
      "elements": [...],
      "coverage_pct": 95.0,
      "summary": "Standard earthwork excavation with detailed material breakdown"
    }
  ]
}
```

### `GET /pricing/market-prices`

**Query Parameters**
| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `zone` | string | "A" | Construction zone |

**Response (200)
```json
{
  "success": true,
  "zone": "A",
  "last_updated": "2026-07-20T14:30:00Z",
  "source": "market_rate_service",
  "materials": {
    "sand": { "unit": "m3", "rate": 75.0, "currency": "BDT" },
    "cement": { "unit": "bags", "rate": 350.0, "currency": "BDT" },
    "steel": { "unit": "kg", "rate": 0.85, "currency": "BDT" }
  },
  "labor": {
    "unskilled": { "unit": "man-day", "rate": 450.0, "currency": "BDT" },
    "skilled": { "unit": "man-day", "rate": 650.0, "currency": "BDT" }
  },
  "equipment": {
    "excavator": { "unit": "hour", "rate": 3500.0, "currency": "BDT" },
    "truck": { "unit": "trip", "rate": 2500.0, "currency": "BDT" }
  },
  "indices": {
    "inflation_adjustment": 0.08,
    "regional_premium": 0.05
  }
}
```

### `GET /pricing/compositions`

**Response (200)
```json
{
  "success": true,
  "count": 85,
  "compositions": [
    {
      "sor_code": "40-200-00",
      "elements": 5,
      "materials": 2,
      "labor": 2,
      "equipment": 1
    },
    {
      "sor_code": "26.50.1",
      "elements": 3,
      "materials": 1,
      "labor": 1,
      "equipment": 1
    }
  ]
}
```

---

## Error Codes

| Code | HTTP | Scenario |
|------|------|----------|
| `PRICING_INVALID_INPUT` | 400 | Invalid item data, missing required fields |
| `PRICING_SOR_NOT_FOUND` | 404 | Item code not found in SOR |
| `PRICING_RATE_CALCULATION_FAILED` | 500 | Error calculating rates |

---

## Permission Requirements

| Endpoint | Role | Notes |
|----------|------|-------|
| `/estimate`, `/rate-analysis/*` | `viewer` or higher | Read pricing data |
| `/rate-analysis/from-compare` | `estimator` or `admin` | Write analysis results |

---

## Rate Limits

| Endpoint | Limit | Window |
|----------|-------|--------|
| `/estimate` | 120 | 60 |
| `/rate-analysis` | 30 | 60 |
| `/market-prices` | 60 | 60 |

---

## Caching

- `GET /estimate`, `GET /market-prices`: `public, max-age=3600` (prices change slowly)
- `GET /compositions`: `public, max-age=86400` (composition templates stable)
- Other: `private, max-age=300` (user-specific calculations)

---

## React Query Mapping

```typescript
export const pricingKeys = {
  all: () => ['pricing'] as const,
  estimate: (params: EstimateParams) => 
    [...pricingKeys.all, 'estimate', params] as const,
  marketPrices: (zone: string) => 
    [...pricingKeys.all, 'marketPrices', { zone }] as const,
  compositions: () => [...pricingKeys.all, 'compositions'] as const,
  rateAnalysis: () => [...pricingKeys.all, 'rateAnalysis'] as const,
};

export function usePricingEstimate(params: EstimateParams) {
  return useQuery({
    queryKey: pricingKeys.estimate(params),
    queryFn: () => apiFetch<PricingEstimateResponse>('/pricing/estimate', { params }),
    staleTime: 60_000,
  });
}

export function useMarketPrices(zone = 'A') {
  return useQuery({
    queryKey: pricingKeys.marketPrices(zone),
    queryFn: () => apiFetch<MarketPricesResponse>('/pricing/market-prices', { params: { zone } }),
    staleTime: 60_000 * 60, // 1 hour
  });
}
```

---

## Integration Points

### BOQ Comparison Pipeline
```
POST /boq/compare → Celery job → run_compare_flow() → 
  BOQProcessor.compare() → 
    SOR lookup for each item → 
    Build rate analysis → 
      POST /pricing/rate-analysis/from-compare (for detailed analysis)
```

### Pricing Optimization
```
POST /pricing/estimate → SOR + fuzzy matches → 
  POST /pricing/rate-analysis/from-compare → Profit margins analysis → 
  POST /rate-analysis/analyze-items → Element-level breakdown → 
    Update tender with pricing confidence scores
```

### Competitor Intelligence
```
GET /pricing/estimate → Market rates + SOR rates → 
  POST /pricing/rate-analysis/analyze-items → 
    Analyze competitor bid positioning → 
    Update win probability score
```

---

## Versioning

- `v1`: Current (direct SOR service integration, rate calculation)
- `v2` (planned): GraphQL pricing queries, real-time market updates

---

## Configuration Options

Environment variables:
- `PRICING_SOR_FALLBACK=true|false` (default: true)
- `PRICING_FUZZY_THRESHOLD=0.42` (default: 0.42)
- `PRICING_CACHE_TTL=3600` (seconds)
- `PRICING_MARKET_SOURCE=market_rate_service` (alternative providers)

---

## Monitoring & Telemetry

**Metrics**:
- Items matched vs. unmatched
- Average confidence scores
- Processing time by item type
- SOR cache hit/miss rates
- Market rate update frequency

**Alerts**:
- High pricing variance > 15%
- SOR not found > 10% of items
- Market rate drift > 5%

> **Dependency**: `app/sor/sor_service.py` → `find_rate()`, `find_rate_by_description()`
> **Dependency**: `app/services/rate_analysis_engine.py` → `analyze_boq_items()`
> **Integration**: `/api/boq/compare` → `/api/pricing/rate-analysis/from-compare` (composite analysis)

---

## OpenAPI Reference

See `/openapi.json#/paths/~1api~1pricing~1estimate/post`