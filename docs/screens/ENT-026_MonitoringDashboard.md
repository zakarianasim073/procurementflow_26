# ENT-026: Monitoring Dashboard Screen Specification

**Module:** `features/monitoring-dashboard/MonitoringDashboardPage`
**Layer:** features
**Version:** 1.0.0
**Status:** Draft
**Workspace:** Settings

## Purpose
Real-time system monitoring, health checks, and alerting.

## Screen Layout

```
┌─────────────────────────────────────────────────────────────┐
│ ExecutiveHeader                                             │
├──────────┬──────────────────────────────────────────────────┤
│          │ Breadcrumb: Settings > Monitoring Dashboard       │
│ Workspace├──────────────────────────────────────────────────┤
│   Nav    │ MonitoringDashboardHeader (status, alerts)       │
│          ├──────────────────────────────────────────────────┤
│          │ MonitoringDashboard (main content)               │
│          │ ┌────────────────────────────────────────────┐   │
│          │ │ StatusOverview (health indicators)          │   │
│          │ ├────────────────────────────────────────────┤   │
│          │ │ Tabs: [Real-time] [History] [Alerts]        │   │
│          │ ├────────────────────────────────────────────┤   │
│          │ │ RealTimeTab (live metrics)                  │   │
│          │ │ HistoryTab (historical data)                │   │
│          │ │ AlertsTab (alert rules)                     │   │
│          │ └────────────────────────────────────────────┘   │
├──────────┴──────────────────────────────────────────────────┤
│ AiDock (monitoring insights)                                │
└─────────────────────────────────────────────────────────────┘
```

## Component Tree

```
MonitoringDashboardPage
├── ExecutiveHeader
├── Breadcrumb
├── MonitoringDashboardHeader
│   ├── KpiStrip (service_count, healthy_count, alert_count)
│   └── Button (Run Health Check)
├── MonitoringDashboard
│   ├── StatusOverview
│   │   ├── ServiceStatus × N
│   │   │   ├── name
│   │   │   ├── status
│   │   │   ├── uptime
│   │   │   └── last_check
│   │   └── OverallHealth
│   │       ├── health_score
│   │       └── health_trend
│   ├── Tabs
│   │   ├── RealTimeTab
│   │   │   ├── Chart (cpu_usage)
│   │   │   ├── Chart (memory_usage)
│   │   │   ├── Chart (network_usage)
│   │   │   └── Chart (request_rate)
│   │   ├── HistoryTab
│   │   │   ├── CalendarRange
│   │   │   ├── Chart (historical_metrics)
│   │   │   └── Table<MetricEntry>
│   │   └── AlertsTab
│   │       ├── AlertRules
│   │       │   └── RuleCard × N
│   │       │       ├── metric
│   │       │       ├── threshold
│   │       │       └── status
│   │       └── AlertHistory
│   │           └── AlertEntry × N
│   │               ├── timestamp
│   │               ├── metric
│   │               └── value
│   └── ServiceDetails
│       ├── service_info
│       ├── metrics
│       └── logs
└── AiDock
    ├── AgentCard (Monitoring Agent)
    └── EvidencePanel (monitoring insights)
```

## Data Sources

### Monitoring Data
```typescript
// API: GET /api/v1/admin/monitoring
interface MonitoringData {
  services: ServiceStatus[];
  metrics: RealTimeMetrics;
  alerts: AlertRule[];
}

interface ServiceStatus {
  service_id: string;
  name: string;
  status: 'healthy' | 'degraded' | 'down';
  uptime: number;
  last_check: string;
  response_time: number;
}

interface RealTimeMetrics {
  cpu_usage: number;
  memory_usage: number;
  disk_usage: number;
  network_in: number;
  network_out: number;
  request_rate: number;
  error_rate: number;
}

interface AlertRule {
  rule_id: string;
  metric: string;
  threshold: number;
  operator: 'gt' | 'lt' | 'eq';
  status: 'active' | 'inactive';
  last_triggered?: string;
}
```

### React Query
```typescript
const { data: monitoring } = useQuery({
  queryKey: ['admin', 'monitoring'],
  queryFn: () => api.get('/api/v1/admin/monitoring'),
  refetchInterval: 10_000, // 10 seconds
});

const runHealthCheck = useMutation({
  mutationFn: () => api.post('/api/v1/admin/monitoring/health-check'),
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ['admin', 'monitoring'] });
    toast.success('Health check completed');
  },
});
```

## Zustand Store
```typescript
// stores/monitoringDashboardStore.ts
interface MonitoringDashboardState {
  activeTab: string;
  setTab: (tab: string) => void;
}
```

## Interactions

### View Real-time
1. Click Real-time tab
2. View live metrics
3. Monitor usage
4. Check services

### View History
1. Click History tab
2. Set date range
3. View trends
4. Analyze patterns

### Manage Alerts
1. Click Alerts tab
2. View rules
3. Edit thresholds
4. Enable/disable

### Run Health Check
1. Click Health Check
2. Execute checks
3. Display results
4. Update status

## Responsive Breakpoints

| Breakpoint | Layout |
|------------|--------|
| Desktop (>1024px) | Full tabs + charts |
| Tablet (768-1024px) | Stacked tabs |
| Mobile (<768px) | Simplified view |

## Loading States
- Services: Loading indicators
- Metrics: Loading charts
- Alerts: Loading rules

## Error States
- Check failure: Retry button
- Alert failure: Error details
- Network error: Toast notification

## Accessibility
- Services are focusable
- Status announced via `aria-live`
- Screen reader: "Service: API, status: healthy"
- Keyboard: Tab through services

## Telemetry
- `monitoring_dashboard.view` — Screen loaded
- `monitoring_dashboard.health_check` — Health check run
- `monitoring_dashboard.alert_edit` — Alert edited

## Implementation Notes
- Real-time monitoring
- Historical trends
- Alert management
- AiDock provides monitoring insights
- Service health tracking
