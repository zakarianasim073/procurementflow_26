# Dashboard API Contract

**Router**: `/api/v1/dashboard`  
**Tags**: `dashboard`  
**Auth**: Optional JWT (tenant-scoped if authenticated)

---

## Endpoint Catalog

| Method | Path | Purpose | Auth |
|--------|------|---------|------|
| GET | `/dashboard/stats` | Aggregate counts (tenders, comparisons, BOQ items) | Optional JWT |
| GET | `/dashboard/analytics` | Charts: by agency, monthly, flag distribution | Optional JWT |
| GET | `/dashboard/data-intelligence` | DB-backed intelligence stats | Optional JWT |
| POST | `/dashboard/data-intelligence/collect` | Trigger live data collection | Optional JWT |
| GET | `/dashboard/bwdb-monitor` | BWDB monitor stats + alert history | Optional JWT |
| POST | `/dashboard/bwdb-monitor/scan` | Scan BWDB tenders for high-value alerts | Optional JWT |

---

## Request/Response Schemas

### `GET /dashboard/stats`

**Query**: None (uses auth context for tenant scoping)

**Response (200)**
```json
{
  "success": true,
  "stats": {
    "total_tenders": 1247,
    "total_comparisons": 389,
    "total_boq_items": 15234,
    "recent_comparisons": [
      {
        "id": "cmp-uuid",
        "boq_file_id": "abc123",
        "total_items": 245,
        "matches": 198,
        "variances": 32,
        "mismatches": 15,
        "created_at": "2026-07-15T10:30:00Z"
      }
    ],
    "tender_status": {
      "ACTIVE": 892,
      "CLOSED": 312,
      "ARCHIVED": 43
    }
  }
}
```

**Tenant Scoping**: If authenticated, filters to `owner_id = user.id`. Guest sees global (demo) data.

---

### `GET /dashboard/analytics`

**Response (200)**
```json
{
  "success": true,
  "analytics": {
    "by_agency": [
      { "agency": "BWDB", "count": 156, "avg_discount": 12.34 },
      { "agency": "PWD", "count": 98, "avg_discount": 8.91 }
    ],
    "monthly": [
      { "month": "2026-01", "count": 45 },
      { "month": "2026-02", "count": 52 }
    ],
    "flag_distribution": {
      "MATCH": 1200,
      "BELOW_SOR": 340,
      "ABOVE_SOR": 180,
      "NO_RATE": 95
    }
  }
}
```

---

### `GET /dashboard/data-intelligence`

**Response (200)**
```json
{
  "success": true,
  "lifecycle_stats": {
    "total_records": 238451,
    "matched_packages": 108934,
    "agencies": 12,
    "contractors": 32156
  },
  "contractor_stats": {
    "total_contractors": 32156,
    "with_dna": 28431,
    "avg_npp": 0.876
  },
  "data_quality": {
    "completeness_pct": 94.2,
    "missing_package_no": 1203,
    "orphan_awards": 456
  }
}
```

---

### `POST /dashboard/data-intelligence/collect`

**Request**
```json
{
  "mode": "live|all_tabs|awards|bulk",
  "keyword": "bridge",
  "entity": "BWDB",
  "days": 90,
  "target": 1000,
  "max_pages": 5
}
```

**Response (202)**
```json
{
  "success": true,
  "result": {
    "mode": "live",
    "file": "/runtime/intelligence/live_tenders_20260721.json",
    "records_collected": 247
  },
  "sync": {
    "tenders_imported": 189,
    "awards_imported": 0
  },
  "regime_backfill": { "updated": 45 }
}
```

---

### `GET /dashboard/bwdb-monitor`

**Response (200)**
```json
{
  "success": true,
  "stats": {
    "total_scanned": 15420,
    "high_value_alerts": 23,
    "last_scan": "2026-07-21T06:00:00Z"
  },
  "alerts": [
    {
      "tender_id": "1298004",
      "title": "Major Bridge Construction",
      "estimated_value": 450000000,
      "alert_type": "HIGH_VALUE",
      "created_at": "2026-07-20T14:30:00Z"
    }
  ]
}
```

---

### `POST /dashboard/bwdb-monitor/scan`

**Response (200)**
```json
{
  "success": true,
  "alerts_sent": 3,
  "alerts": [...]
}
```

---

## Error Schema

```json
{
  "detail": "Database connection failed",
  "status_code": 503
}
```

---

## Permission Requirements

| Endpoint | Min Role | Tenant Scope |
|----------|----------|--------------|
| All | `viewer` (or guest) | Own tenant / demo |

---

## Rate Limits

| Endpoint | Limit | Window |
|----------|-------|--------|
| `/stats`, `/analytics` | 60 req | 60 sec |
| `/data-intelligence/collect` | 5 req | 300 sec |
| `/bwdb-monitor/*` | 10 req | 60 sec |

---

## Caching

| Endpoint | Cache-Control | Invalidation |
|----------|---------------|--------------|
| `/stats` | `private, max-age=30` | User action |
| `/analytics` | `private, max-age=60` | Nightly rebuild |
| `/data-intelligence` | `private, max-age=300` | ETL completion |
| `/bwdb-monitor` | `private, max-age=60` | Scan completion |

---

## React Query Mapping

```typescript
// hooks/useDashboard.ts
export const dashboardKeys = {
  stats: ['dashboard', 'stats'] as const,
  analytics: ['dashboard', 'analytics'] as const,
  intelligence: ['dashboard', 'intelligence'] as const,
  bwdb: ['dashboard', 'bwdb'] as const,
};

export function useDashboardStats() {
  return useQuery({
    queryKey: dashboardKeys.stats,
    queryFn: () => apiFetch<DashboardStatsResponse>('/dashboard/stats'),
    staleTime: 30_000,
  });
}

export function useTriggerCollection() {
  return useMutation({
    mutationFn: (payload: CollectPayload) => apiFetch('/dashboard/data-intelligence/collect', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  });
}
```

---

## Zustand Store

```typescript
// stores/dashboard.ts
interface DashboardState {
  lastStats: DashboardStats | null;
  setStats: (s: DashboardStats) => void;
  clearCache: () => void;
}
```

---

## Versioning

- `v1`: Current (tenant-scoped optional auth)
- `v2` (planned): Real-time WebSocket push for stats updates