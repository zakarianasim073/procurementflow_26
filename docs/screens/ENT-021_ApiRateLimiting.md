# ENT-021: API Rate Limiting Screen Specification

**Module:** `features/api-rate-limiting/ApiRateLimitingPage`
**Layer:** features
**Version:** 1.0.0
**Status:** Draft
**Workspace:** Settings

## Purpose
Monitor and configure API rate limiting and throttling.

## Screen Layout

```
┌─────────────────────────────────────────────────────────────┐
│ ExecutiveHeader                                             │
├──────────┬──────────────────────────────────────────────────┤
│          │ Breadcrumb: Settings > API Rate Limiting          │
│ Workspace├──────────────────────────────────────────────────┤
│   Nav    │ ApiRateLimitingHeader (limits, usage)             │
│          ├──────────────────────────────────────────────────┤
│          │ ApiRateLimiting (main content)                    │
│          │ ┌────────────────────────────────────────────┐   │
│          │ │ RateLimitOverview (current limits)          │   │
│          │ ├────────────────────────────────────────────┤   │
│          │ │ UsageChart (API usage)                      │   │
│          │ ├────────────────────────────────────────────┤   │
│          │ │ LimitConfig (configuration)                 │   │
│          │ └────────────────────────────────────────────┘   │
├──────────┴──────────────────────────────────────────────────┤
│ AiDock (rate limiting insights)                             │
└─────────────────────────────────────────────────────────────┘
```

## Component Tree

```
ApiRateLimitingPage
├── ExecutiveHeader
├── Breadcrumb
├── ApiRateLimitingHeader
│   ├── KpiStrip (total_limits, active_limits, violations)
│   └── Button (Add Limit)
├── ApiRateLimiting
│   ├── RateLimitOverview
│   │   ├── LimitCard × N
│   │   │   ├── endpoint
│   │   │   ├── limit
│   │   │   ├── current_usage
│   │   │   └── status
│   │   └── UsageChart
│   │       └── Chart (usage_over_time)
│   ├── LimitConfig
│   │   ├── LimitForm
│   │   │   ├── endpoint
│   │   │   ├── limit
│   │   │   ├── window
│   │   │   └── actions (save, test)
│   │   └── LimitList
│   │       └── LimitRow × N
│   │           ├── endpoint
│   │           ├── limit
│   │           ├── window
│   │           └── actions (edit, delete)
│   └── ViolationLog
│       └── ViolationEntry × N
│           ├── timestamp
│           ├── endpoint
│           ├── client
│           └── details
└── AiDock
    ├── AgentCard (API Agent)
    └── EvidencePanel (rate limiting insights)
```

## Data Sources

### Rate Limits
```typescript
// API: GET /api/v1/admin/rate-limits
interface RateLimitList {
  limits: RateLimit[];
  total_count: number;
  active_count: number;
  violation_count: number;
}

interface RateLimit {
  limit_id: string;
  endpoint: string;
  limit: number;
  window: number;
  current_usage: number;
  status: 'active' | 'exceeded' | 'disabled';
}
```

### React Query
```typescript
const { data: limits } = useQuery({
  queryKey: ['admin', 'rate-limits'],
  queryFn: () => api.get('/api/v1/admin/rate-limits'),
});

const createLimit = useMutation({
  mutationFn: (limit: CreateLimitRequest) => api.post('/api/v1/admin/rate-limits', limit),
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ['admin', 'rate-limits'] });
    toast.success('Limit created');
  },
});

const deleteLimit = useMutation({
  mutationFn: (limitId: string) => api.delete(`/api/v1/admin/rate-limits/${limitId}`),
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ['admin', 'rate-limits'] });
    toast.success('Limit deleted');
  },
});
```

## Zustand Store
```typescript
// stores/apiRateLimitingStore.ts
interface ApiRateLimitingState {
  selectedLimit: string | null;
  setLimit: (id: string | null) => void;
}
```

## Interactions

### View Limits
1. Click limit card
2. View details
3. Check usage
4. Review status

### Add Limit
1. Click Add Limit
2. Fill form
3. Set parameters
4. Save limit

### Edit Limit
1. Click Edit button
2. Modify settings
3. Save changes
4. Update card

### Delete Limit
1. Click Delete button
2. Confirm deletion
3. Remove limit
4. Update list

## Responsive Breakpoints

| Breakpoint | Layout |
|------------|--------|
| Desktop (>1024px) | Full overview + config |
| Tablet (768-1024px) | Stacked layout |
| Mobile (<768px) | Simplified view |

## Loading States
- Limits: Skeleton cards
- Usage: Loading chart
- Config: Loading form

## Error States
- Load failure: Retry button
- Save failure: Toast error
- Network error: Toast notification

## Accessibility
- Limits are focusable
- Usage announced via `aria-live`
- Screen reader: "Endpoint: /api/tenders, limit: 100/min"
- Keyboard: Tab through limits

## Telemetry
- `api_rate_limiting.view` — Screen loaded
- `api_rate_limiting.add` — Limit added
- `api_rate_limiting.edit` — Limit edited
- `api_rate_limiting.delete` — Limit deleted

## Implementation Notes
- Real-time usage monitoring
- Configurable limits
- Violation logging
- AiDock provides insights
- Export for analysis
