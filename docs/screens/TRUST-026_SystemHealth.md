# TRUST-026: System Health Screen Specification

**Module:** `features/system-health/SystemHealthPage`
**Layer:** features
**Version:** 1.0.0
**Status:** Draft
**Workspace:** Trust

## Purpose
Monitor system health, performance metrics, and service status.

## Screen Layout

```
┌─────────────────────────────────────────────────────────────┐
│ ExecutiveHeader                                             │
├──────────┬──────────────────────────────────────────────────┤
│          │ Breadcrumb: Trust > System Health                 │
│ Workspace├──────────────────────────────────────────────────┤
│   Nav    │ SystemHealthHeader (score, status)               │
│          ├──────────────────────────────────────────────────┤
│          │ SystemHealth (main content)                      │
│          │ ┌────────────────────────────────────────────┐   │
│          │ │ HealthScore (overall health)                │   │
│          │ ├────────────────────────────────────────────┤   │
│          │ │ Tabs: [Services] [Metrics] [Alerts]         │   │
│          │ ├────────────────────────────────────────────┤   │
│          │ │ ServicesTab (service status)                │   │
│          │ │ MetricsTab (performance metrics)            │   │
│          │ │ AlertsTab (health alerts)                   │   │
│          │ └────────────────────────────────────────────┘   │
├──────────┴──────────────────────────────────────────────────┤
│ AiDock (health insights)                                    │
└─────────────────────────────────────────────────────────────┘
```

## Component Tree

```
SystemHealthPage
├── ExecutiveHeader
├── Breadcrumb
├── SystemHealthHeader
│   ├── KpiStrip (health_score, uptime, response_time)
│   └── Button (Run Diagnostics)
├── SystemHealth
│   ├── HealthScore
│   │   ├── score_gauge
│   │   ├── score_history
│   │   └── score_breakdown
│   ├── Tabs
│   │   ├── ServicesTab
│   │   │   └── ServiceList
│   │   │       └── ServiceCard × N
│   │   │           ├── name
│   │   │           ├── status
│   │   │           ├── uptime
│   │   │           ├── response_time
│   │   │           └── Button (View Details)
│   │   ├── MetricsTab
│   │   │   ├── Chart (cpu_usage)
│   │   │   ├── Chart (memory_usage)
│   │   │   ├── Chart (disk_usage)
│   │   │   └── Chart (network_usage)
│   │   └── AlertsTab
│   │       └── AlertList
│   │           └── AlertCard × N
│   │               ├── type
│   │               ├── severity
│   │               ├── message
│   │               └── Button (Dismiss)
│   └── DiagnosticsReport
│       ├── summary
│       ├── findings
│       └── recommendations
└── AiDock
    ├── AgentCard (Health Agent)
    └── EvidencePanel (health insights)
```

## Data Sources

### System Health
```typescript
// API: GET /api/v1/trust/health
interface SystemHealth {
  score: number;
  uptime: number;
  services: ServiceStatus[];
  metrics: SystemMetrics;
  alerts: HealthAlert[];
}

interface ServiceStatus {
  service_id: string;
  name: string;
  status: 'healthy' | 'degraded' | 'down';
  uptime: number;
  response_time: number;
  last_check: string;
}

interface SystemMetrics {
  cpu_usage: number;
  memory_usage: number;
  disk_usage: number;
  network_in: number;
  network_out: number;
}

interface HealthAlert {
  alert_id: string;
  type: string;
  severity: 'info' | 'warning' | 'critical';
  message: string;
  created_at: string;
}
```

### React Query
```typescript
const { data: health } = useQuery({
  queryKey: ['trust', 'health'],
  queryFn: () => api.get('/api/v1/trust/health'),
  refetchInterval: 30_000,
});

const runDiagnostics = useMutation({
  mutationFn: () => api.post('/api/v1/trust/health/diagnostics'),
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ['trust', 'health'] });
    toast.success('Diagnostics completed');
  },
});
```

## Zustand Store
```typescript
// stores/systemHealthStore.ts
interface SystemHealthState {
  activeTab: string;
  setTab: (tab: string) => void;
}
```

## Interactions

### View Services
1. Click Services tab
2. View service list
3. Check status
4. View details

### View Metrics
1. Click Metrics tab
2. View charts
3. Check usage
4. Analyze trends

### View Alerts
1. Click Alerts tab
2. View alert list
3. Check severity
4. Dismiss if needed

### Run Diagnostics
1. Click Run Diagnostics
2. Execute checks
3. View report
4. Take action

## Responsive Breakpoints

| Breakpoint | Layout |
|------------|--------|
| Desktop (>1024px) | Full tabs + panels |
| Tablet (768-1024px) | Stacked tabs |
| Mobile (<768px) | Simplified view |

## Loading States
- Health: Loading score
- Services: Loading list
- Metrics: Loading charts

## Error States
- Diagnostics failure: Retry button
- Alert failure: Error details
- Network error: Toast notification

## Accessibility
- Services are focusable
- Score announced via `aria-live`
- Screen reader: "System health: 95/100"
- Keyboard: Tab through services

## Telemetry
- `system_health.view` — Screen loaded
- `system_health.diagnostics` — Diagnostics run
- `system_health.alert_dismiss` — Alert dismissed

## Implementation Notes
- Real-time health monitoring
- Service status tracking
- Performance metrics
- AiDock provides health insights
- Export for reporting
