# TRUST-003: System Health Screen Specification

**Module:** `features/system/SystemHealthPage`
**Layer:** features
**Version:** 1.0.0
**Status:** Draft
**Workspace:** Trust

## Purpose
System monitoring, performance metrics, error tracking, and infrastructure health dashboard.

## Screen Layout

```
┌─────────────────────────────────────────────────────────────┐
│ ExecutiveHeader                                             │
├──────────┬──────────────────────────────────────────────────┤
│          │ Breadcrumb: Trust > System Health                 │
│ Workspace├──────────────────────────────────────────────────┤
│   Nav    │ SystemHealthHeader (status, refresh)             │
│          ├──────────────────────────────────────────────────┤
│          │ SystemHealthMonitor (main content)               │
│          │ ┌────────────────────────────────────────────┐   │
│          │ │ StatusBanner (overall health)               │   │
│          │ ├────────────────────────────────────────────┤   │
│          │ │ MetricsGrid:                               │   │
│          │ │ ┌──────────┐ ┌──────────┐ ┌──────────┐     │   │
│          │ │ │ CPU      │ │ Memory   │ │ Disk     │     │   │
│          │ │ │ 45%      │ │ 62%      │ │ 78%      │     │   │
│          │ │ └──────────┘ └──────────┘ └──────────┘     │   │
│          │ ├────────────────────────────────────────────┤   │
│          │ │ ServicesStatus (table)                      │   │
│          │ │ Service | Status | Uptime | Response        │   │
│          │ ├────────────────────────────────────────────┤   │
│          │ │ ErrorLog (recent errors)                    │   │
│          │ │ Time | Level | Message | Source             │   │
│          │ └────────────────────────────────────────────┘   │
├──────────┴──────────────────────────────────────────────────┤
│ TrustPanel (AI model status, queue health)                  │
└─────────────────────────────────────────────────────────────┘
```

## Component Tree

```
SystemHealthPage
├── ExecutiveHeader
├── Breadcrumb
├── SystemHealthHeader
│   ├── Badge (status: healthy/degraded/unhealthy)
│   ├── Button (Refresh)
│   └── Button (Export Report)
├── SystemHealthMonitor
│   ├── StatusBanner
│   │   ├── Badge (overall status)
│   │   └── last_check timestamp
│   ├── MetricsGrid
│   │   ├── Gauge (cpu_usage)
│   │   ├── Gauge (memory_usage)
│   │   ├── Gauge (disk_usage)
│   │   ├── Gauge (network_io)
│   │   ├── Gauge (request_rate)
│   │   └── Gauge (error_rate)
│   ├── ServicesStatus
│   │   └── Table<Service>
│   │       ├── name
│   │       ├── status
│   │       ├── uptime
│   │       ├── response_time
│   │       └── last_check
│   └── ErrorLog
│       └── Table<ErrorEntry>
│           ├── timestamp
│           ├── level
│           ├── message
│           └── source
└── TrustPanel
```

## Data Sources

### System Metrics
```typescript
// API: GET /api/v1/admin/system/health
interface SystemHealth {
  status: 'healthy' | 'degraded' | 'unhealthy';
  last_check: string;
  metrics: {
    cpu_usage: number;
    memory_usage: number;
    disk_usage: number;
    network_io: number;
    request_rate: number;
    error_rate: number;
  };
  services: ServiceStatus[];
}

interface ServiceStatus {
  name: string;
  status: 'running' | 'stopped' | 'error';
  uptime: number;
  response_time: number;
  last_check: string;
  error?: string;
}
```

### Error Log
```typescript
// API: GET /api/v1/admin/system/errors
interface ErrorLog {
  errors: ErrorEntry[];
  total_count: number;
}

interface ErrorEntry {
  error_id: string;
  timestamp: string;
  level: 'error' | 'warning' | 'info';
  message: string;
  source: string;
  stack_trace?: string;
  count: number;
}
```

### React Query
```typescript
const { data: health } = useQuery({
  queryKey: ['admin', 'system', 'health'],
  queryFn: () => api.get('/api/v1/admin/system/health'),
  refetchInterval: 30_000, // 30 seconds
});

const { data: errors } = useQuery({
  queryKey: ['admin', 'system', 'errors', filters],
  queryFn: () => api.get('/api/v1/admin/system/errors', { params: filters }),
});

const refreshHealth = useMutation({
  mutationFn: () => api.post('/api/v1/admin/system/health/refresh'),
});
```

## Zustand Store
```typescript
// stores/systemHealthStore.ts
interface SystemHealthState {
  autoRefresh: boolean;
  refreshInterval: number;
  errorFilter: string[];
  setAutoRefresh: (enabled: boolean) => void;
  setRefreshInterval: (interval: number) => void;
  setErrorFilter: (filter: string[]) => void;
}
```

## Interactions

### Refresh Metrics
1. Click Refresh button
2. POST refresh API
3. Update all metrics
4. Show last check time

### Service Details
1. Click service row
2. Open ServiceDrawer
3. View detailed metrics
4. View logs

### Error Investigation
1. Click error row
2. Open ErrorDrawer
3. View stack trace
4. View related errors

### Auto-Refresh
1. Toggle auto-refresh
2. Set interval (10s, 30s, 1m)
3. Poll metrics automatically
4. Update charts in real-time

## Responsive Breakpoints

| Breakpoint | Layout |
|------------|--------|
| Desktop (>1024px) | Full grid + tables |
| Tablet (768-1024px) | Stacked metrics |
| Mobile (<768px) | Single column, collapsible |

## Loading States
- Metrics: Skeleton gauges
- Services: Skeleton table
- Errors: Skeleton rows

## Error States
- Health check failure: Warning banner
- Service down: Red status badge
- High error rate: Alert notification

## Accessibility
- Metrics announced via `aria-live`
- Status changes highlighted
- Screen reader: "CPU usage: 45%"
- Keyboard: Tab through metrics

## Telemetry
- `system_health.view` — Screen loaded
- `system_health.refresh` — Metrics refreshed
- `system_health.service_click` — Service selected
- `system_health.error_click` — Error selected

## Implementation Notes
- Real-time metrics via polling
- Gauge components for visualization
- Service status table
- Error log with filtering
- AiDock provides system insights
