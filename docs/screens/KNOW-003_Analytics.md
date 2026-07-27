# KNOW-003: Analytics Dashboard Screen Specification

**Module:** `features/analytics/AnalyticsPage`
**Layer:** features
**Version:** 1.0.0
**Status:** Draft
**Workspace:** Knowledge

## Purpose
Performance analytics, trend visualization, ROI tracking, and business intelligence for procurement operations.

## Screen Layout

```
┌─────────────────────────────────────────────────────────────┐
│ ExecutiveHeader                                             │
├──────────┬──────────────────────────────────────────────────┤
│          │ Breadcrumb: Knowledge > Analytics                 │
│ Workspace├──────────────────────────────────────────────────┤
│   Nav    │ AnalyticsHeader (date range, metrics)            │
│          ├──────────────────────────────────────────────────┤
│          │ AnalyticsDashboard (main content)                │
│          │ ┌────────────────────────────────────────────┐   │
│          │ │ KpiStrip (8 key metrics)                   │   │
│          │ ├────────────────────────────────────────────┤   │
│          │ │ Charts Grid:                               │   │
│          │ │ ┌──────────────┐ ┌──────────────┐          │   │
│          │ │ │ WinRateChart │ │ ValueChart   │          │   │
│          │ │ │ (line)       │ │ (bar)        │          │   │
│          │ │ └──────────────┘ └──────────────┘          │   │
│          │ │ ┌──────────────┐ ┌──────────────┐          │   │
│          │ │ │ AgencyChart  │ │ ZoneChart    │          │   │
│          │ │ │ (pie)        │ │ (heatmap)    │          │   │
│          │ │ └──────────────┘ └──────────────┘          │   │
│          │ ├────────────────────────────────────────────┤   │
│          │ │ InsightsPanel (AI recommendations)         │   │
│          │ └────────────────────────────────────────────┘   │
├──────────┴──────────────────────────────────────────────────┤
│ AiDock (analytics insights, trend predictions)              │
└─────────────────────────────────────────────────────────────┘
```

## Component Tree

```
AnalyticsPage
├── ExecutiveHeader
├── Breadcrumb
├── AnalyticsHeader
│   ├── CalendarRange (date range)
│   ├── ChipSelect (agencies)
│   ├── ChipSelect (zones)
│   └── Button (Export Report)
├── AnalyticsDashboard
│   ├── KpiStrip
│   │   ├── KpiCard (total_tenders)
│   │   ├── KpiCard (win_rate)
│   │   ├── KpiCard (total_value)
│   │   ├── KpiCard (avg_bid_value)
│   │   ├── KpiCard (competition_ratio)
│   │   ├── KpiCard (response_time)
│   │   ├── KpiCard (success_rate)
│   │   └── KpiCard (roi)
│   ├── ChartsGrid
│   │   ├── WinRateChart (line)
│   │   ├── ValueChart (bar)
│   │   ├── AgencyChart (pie)
│   │   └── ZoneChart (heatmap)
│   └── InsightsPanel
│       └── AiInsight × N
│           ├── icon
│           ├── title
│           ├── description
│           └── ConfidenceBadge
└── AiDock
    ├── AgentCard (Intelligence Agent)
    └── EvidencePanel (analytics insights)
```

## Data Sources

### Analytics Metrics
```typescript
// API: GET /api/v1/knowledge/analytics
interface AnalyticsMetrics {
  total_tenders: number;
  win_rate: number;
  total_value: number;
  avg_bid_value: number;
  competition_ratio: number;
  avg_response_time: number;
  success_rate: number;
  roi: number;
  trends: {
    metric: string;
    current: number;
    previous: number;
    change_pct: number;
  }[];
}
```

### Chart Data
```typescript
// API: GET /api/v1/knowledge/analytics/charts
interface ChartData {
  win_rate_trend: { date: string; value: number }[];
  value_distribution: { agency: string; value: number }[];
  zone_activity: { zone: string; count: number; value: number }[];
  agency_performance: { agency: string; wins: number; losses: number }[];
}
```

### AI Insights
```typescript
// API: GET /api/v1/knowledge/analytics/insights
interface AiInsight {
  insight_id: string;
  type: 'trend' | 'anomaly' | 'recommendation' | 'warning';
  title: string;
  description: string;
  confidence: number;
  evidence: string;
  created_at: string;
}
```

### React Query
```typescript
const { data: metrics } = useQuery({
  queryKey: ['knowledge', 'analytics', dateRange],
  queryFn: () => api.get('/api/v1/knowledge/analytics', { params: dateRange }),
});

const { data: charts } = useQuery({
  queryKey: ['knowledge', 'analytics', 'charts', dateRange],
  queryFn: () => api.get('/api/v1/knowledge/analytics/charts', { params: dateRange }),
});

const { data: insights } = useQuery({
  queryKey: ['knowledge', 'analytics', 'insights'],
  queryFn: () => api.get('/api/v1/knowledge/analytics/insights'),
});
```

## Zustand Store
```typescript
// stores/analyticsStore.ts
interface AnalyticsState {
  dateRange: { start: string; end: string };
  selectedAgencies: string[];
  selectedZones: string[];
  setDateRange: (range: { start: string; end: string }) => void;
  setAgencies: (agencies: string[]) => void;
  setZones: (zones: string[]) => void;
}
```

## Interactions

### Date Range Change
1. Click CalendarRange
2. Select new range
3. Refetch all metrics
4. Update charts

### Chart Interaction
1. Hover for tooltip
2. Click data point
3. Drill down to details
4. Compare with other charts

### Insight Click
1. Click insight card
2. Expand details
3. View evidence
4. Take action (if recommendation)

### Export Report
1. Click Export button
2. Choose format (PDF/Excel)
3. Include all metrics
4. Download report

## Responsive Breakpoints

| Breakpoint | Layout |
|------------|--------|
| Desktop (>1024px) | 2x2 chart grid |
| Tablet (768-1024px) | Stacked charts |
| Mobile (<768px) | Single column, scrollable |

## Loading States
- KPIs: Skeleton cards
- Charts: Skeleton with shimmer
- Insights: Skeleton cards

## Error States
- No data: EmptyState
- API error: Toast notification
- Partial data: Show available

## Accessibility
- Charts have table fallback
- KPIs announced via `aria-live`
- Screen reader: "Win rate: 45%, up 5%"
- Keyboard: Tab through charts

## Telemetry
- `analytics.view` — Screen loaded
- `analytics.date_range` — Range changed
- `analytics.chart_click` — Chart interacted
- `analytics.export` — Report exported

## Implementation Notes
- KpiStrip shows key metrics
- Charts use Chart component
- Insights powered by AI
- AiDock provides analytics insights
- Export generates analytics report
