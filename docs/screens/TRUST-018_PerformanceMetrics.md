# TRUST-018: Performance Metrics Screen Specification

**Module:** `features/performance-metrics/PerformanceMetricsPage`
**Layer:** features
**Version:** 1.0.0
**Status:** Draft
**Workspace:** Trust

## Purpose
Monitor system performance, response times, and resource usage.

## Screen Layout

```
┌─────────────────────────────────────────────────────────────┐
│ ExecutiveHeader                                             │
├──────────┬──────────────────────────────────────────────────┤
│          │ Breadcrumb: Trust > Performance Metrics           │
│ Workspace├──────────────────────────────────────────────────┤
│   Nav    │ PerformanceMetricsHeader (score, uptime)         │
│          ├──────────────────────────────────────────────────┤
│          │ PerformanceMetrics (main content)                │
│          │ ┌────────────────────────────────────────────┐   │
│          │ │ MetricsOverview (summary)                   │   │
│          │ ├────────────────────────────────────────────┤   │
│          │ │ Tabs: [Real-time] [Historical] [Alerts]     │   │
│          │ ├────────────────────────────────────────────┤   │
│          │ │ RealTimeMetrics (live data)                 │   │
│          │ │ HistoricalMetrics (trends)                  │   │
│          │ │ PerformanceAlerts (thresholds)              │   │
│          │ └────────────────────────────────────────────┘   │
├──────────┴──────────────────────────────────────────────────┤
│ AiDock (performance insights)                               │
└─────────────────────────────────────────────────────────────┘
```

## Component Tree

```
PerformanceMetricsPage
├── ExecutiveHeader
├── Breadcrumb
├── PerformanceMetricsHeader
│   ├── KpiStrip (performance_score, uptime, avg_response)
│   └── Button (Run Benchmark)
├── PerformanceMetrics
│   ├── MetricsOverview
│   │   ├── Gauge (performance_score)
│   │   ├── Chart (uptime_history)
│   │   └── Chart (response_time)
│   ├── Tabs
│   │   ├── RealTimeTab
│   │   │   └── RealTimeMetrics
│   │   │       ├── cpu_usage
│   │   │       ├── memory_usage
│   │   │       ├── disk_usage
│   │   │       └── network_usage
│   │   ├── HistoricalTab
│   │   │   └── HistoricalMetrics
│   │   │       ├── Chart (cpu_trend)
│   │   │       ├── Chart (memory_trend)
│   │   │       └── Chart (response_trend)
│   │   └── AlertsTab
│   │       └── PerformanceAlerts
│   │           └── AlertRule × N
│   │               ├── metric
│   │               ├── threshold
│   │               └── status
│   └── BenchmarkResults
│       └── Benchmark × N
│           ├── name
│           ├── score
│           └── details
└── AiDock
    ├── AgentCard (Performance Agent)
    └── EvidencePanel (performance insights)
```

## Data Sources

### Performance Metrics
```typescript
// API: GET /api/v1/trust/performance
interface PerformanceMetrics {
  score: number;
  uptime: number;
  avg_response_time: number;
  real_time: RealTimeMetrics;
  historical: HistoricalMetrics;
}

interface RealTimeMetrics {
  cpu_usage: number;
  memory_usage: number;
  disk_usage: number;
  network_usage: number;
  active_connections: number;
}

interface HistoricalMetrics {
  cpu_trend: { timestamp: string; value: number }[];
  memory_trend: { timestamp: string; value: number }[];
  response_trend: { timestamp: string; value: number }[];
}
```

### React Query
```typescript
const { data: metrics } = useQuery({
  queryKey: ['trust', 'performance'],
  queryFn: () => api.get('/api/v1/trust/performance'),
  refetchInterval: 10_000, // 10 seconds
});

const runBenchmark = useMutation({
  mutationFn: () => api.post('/api/v1/trust/performance/benchmark'),
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ['trust', 'performance'] });
    toast.success('Benchmark completed');
  },
});
```

## Zustand Store
```typescript
// stores/performanceMetricsStore.ts
interface PerformanceMetricsState {
  activeTab: string;
  setTab: (tab: string) => void;
}
```

## Interactions

### View Real-time
1. Click Real-time tab
2. View live metrics
3. Monitor usage
4. Check connections

### View Historical
1. Click Historical tab
2. View trends
3. Analyze patterns
4. Compare periods

### Run Benchmark
1. Click Run Benchmark
2. Execute tests
3. Display results
4. Update score

### Configure Alerts
1. Click Alerts tab
2. Set thresholds
3. Enable alerts
4. Save configuration

## Responsive Breakpoints

| Breakpoint | Layout |
|------------|--------|
| Desktop (>1024px) | Full metrics + charts |
| Tablet (768-1024px) | Stacked layout |
| Mobile (<768px) | Simplified view |

## Loading States
- Metrics: Loading animation
- Charts: Loading data
- Benchmark: Progress indicator

## Error States
- Load failure: Retry button
- Benchmark failure: Error details
- Network error: Toast notification

## Accessibility
- Metrics are focusable
- Values announced via `aria-live`
- Screen reader: "CPU usage: 45%"
- Keyboard: Tab through metrics

## Telemetry
- `performance_metrics.view` — Screen loaded
- `performance_metrics.benchmark` — Benchmark run
- `performance_metrics.alert_change` — Alert configured

## Implementation Notes
- Real-time monitoring
- Historical trends
- Benchmark testing
- AiDock provides performance insights
- Export for analysis
