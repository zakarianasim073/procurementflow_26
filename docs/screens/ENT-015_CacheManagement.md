# ENT-015: Cache Management Screen Specification

**Module:** `features/cache/CacheManagementPage`
**Layer:** features
**Version:** 1.0.0
**Status:** Draft
**Workspace:** Settings

## Purpose
Cache monitoring, invalidation, and performance optimization.

## Screen Layout

```
┌─────────────────────────────────────────────────────────────┐
│ ExecutiveHeader                                             │
├──────────┬──────────────────────────────────────────────────┤
│          │ Breadcrumb: Settings > Cache Management           │
│ Workspace├──────────────────────────────────────────────────┤
│   Nav    │ CacheManagementHeader (status, hit rate)         │
│          ├──────────────────────────────────────────────────┤
│          │ CacheManagement (main content)                   │
│          │ ┌────────────────────────────────────────────┐   │
│          │ │ CacheStats (hit rate, size, keys)           │   │
│          │ ├────────────────────────────────────────────┤   │
│          │ │ Tabs: [Overview] [Keys] [Patterns] [Config]│   │
│          │ ├────────────────────────────────────────────┤   │
│          │ │ CacheOverview (summary charts)              │   │
│          │ │ KeyList (cache entries)                     │   │
│          │ │ PatternAnalysis (key patterns)              │   │
│          │ │ ConfigurationForm (TTL, limits)             │   │
│          │ └────────────────────────────────────────────┘   │
├──────────┴──────────────────────────────────────────────────┤
│ AiDock (cache insights, optimization)                       │
└─────────────────────────────────────────────────────────────┘
```

## Component Tree

```
CacheManagementPage
├── ExecutiveHeader
├── Breadcrumb
├── CacheManagementHeader
│   ├── KpiStrip (hit_rate, miss_rate, key_count, memory_used)
│   └── Button (Clear Cache)
├── CacheManagement
│   ├── CacheStats
│   │   ├── KpiCard (hit_rate)
│   │   ├── KpiCard (miss_rate)
│   │   ├── KpiCard (key_count)
│   │   └── KpiCard (memory_used)
│   ├── Tabs
│   │   ├── OverviewTab
│   │   │   └── CacheOverview
│   │   │       ├── Chart (hit_rate_trend)
│   │   │       ├── Chart (memory_usage)
│   │   │       └── KpiStrip (detailed_metrics)
│   │   ├── KeysTab
│   │   │   └── KeyList
│   │   │       └── Table<CacheKey>
│   │   │           ├── key
│   │   │           ├── size
│   │   │           ├── ttl
│   │   │           ├── hits
│   │   │           └── Button (Invalidate)
│   │   ├── PatternsTab
│   │   │   └── PatternAnalysis
│   │   │       ├── Table<KeyPattern>
│   │   │       │   ├── pattern
│   │   │       │   ├── count
│   │   │       │   └── hit_rate
│   │   │       └── Chart (pattern_distribution)
│   │   └── ConfigTab
│   │       └── ConfigurationForm
│   │           ├── Input (default_ttl)
│   │           ├── Input (max_memory)
│   │           ├── Input (eviction_policy)
│   │           └── Button (Save)
│   └── CacheActions
│       ├── Button (Clear All)
│       ├── Button (Clear Pattern)
│       └── Button (Export Stats)
└── AiDock
    ├── AgentCard (Performance Agent)
    └── EvidencePanel (cache insights)
```

## Data Sources

### Cache Stats
```typescript
// API: GET /api/v1/admin/cache/stats
interface CacheStats {
  hit_rate: number;
  miss_rate: number;
  key_count: number;
  memory_used: number;
  memory_total: number;
  uptime: number;
  evictions: number;
}
```

### Cache Keys
```typescript
// API: GET /api/v1/admin/cache/keys
interface CacheKeyList {
  keys: CacheKey[];
  total_count: number;
}

interface CacheKey {
  key: string;
  size: number;
  ttl: number;
  hits: number;
  last_accessed: string;
  created_at: string;
}
```

### React Query
```typescript
const { data: stats } = useQuery({
  queryKey: ['admin', 'cache', 'stats'],
  queryFn: () => api.get('/api/v1/admin/cache/stats'),
  refetchInterval: 30_000, // 30 seconds
});

const { data: keys } = useQuery({
  queryKey: ['admin', 'cache', 'keys', filters],
  queryFn: () => api.get('/api/v1/admin/cache/keys', { params: filters }),
});

const clearCache = useMutation({
  mutationFn: (pattern?: string) => api.post('/api/v1/admin/cache/clear', { pattern }),
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ['admin', 'cache'] });
    toast.success('Cache cleared');
  },
});

const invalidateKey = useMutation({
  mutationFn: (key: string) => api.delete(`/api/v1/admin/cache/keys/${key}`),
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ['admin', 'cache'] });
    toast.success('Key invalidated');
  },
});
```

## Zustand Store
```typescript
// stores/cacheManagementStore.ts
interface CacheManagementState {
  activeTab: string;
  setTab: (tab: string) => void;
}
```

## Interactions

### View Stats
1. View cache statistics
2. Analyze hit/miss rates
3. Review memory usage
4. Monitor trends

### Clear Cache
1. Click Clear button
2. Choose pattern (optional)
3. Confirm clear
4. Update stats

### Invalidate Key
1. Click Invalidate button
2. Confirm invalidation
3. Remove key
4. Update list

### Configure Cache
1. Click Config tab
2. Edit settings
3. Save changes
4. Apply configuration

## Responsive Breakpoints

| Breakpoint | Layout |
|------------|--------|
| Desktop (>1024px) | Full tabs with tables |
| Tablet (768-1024px) | Stacked tabs |
| Mobile (<768px) | Single tab view |

## Loading States
- Stats: Skeleton cards
- Keys: Skeleton table
- Config: Skeleton form

## Error States
- Clear failure: Toast error
- Invalidate failure: Toast error
- Network error: Retry button

## Accessibility
- Stats announced via `aria-live`
- Keys are focusable
- Screen reader: "Hit rate: 85%"
- Keyboard: Enter to invalidate, Tab to navigate

## Telemetry
- `cache_management.view` — Screen loaded
- `cache_management.clear` — Cache cleared
- `cache_management.invalidate` — Key invalidated
- `cache_management.config_change` — Config updated

## Implementation Notes
- Real-time cache monitoring
- Key management with CRUD
- Pattern analysis
- AiDock provides cache insights
- Export for performance analysis
