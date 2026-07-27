# EXEC-008: Executive Summary Screen Specification

**Module:** `features/executive-summary/ExecutiveSummaryPage`
**Layer:** features
**Version:** 1.0.0
**Status:** Draft
**Workspace:** Dashboard

## Purpose
High-level executive summary with KPIs, trends, and strategic insights.

## Screen Layout

```
┌─────────────────────────────────────────────────────────────┐
│ ExecutiveHeader                                             │
├──────────┬──────────────────────────────────────────────────┤
│          │ Breadcrumb: Dashboard > Executive Summary         │
│ Workspace├──────────────────────────────────────────────────┤
│   Nav    │ ExecutiveSummaryHeader (period, filters)         │
│          ├──────────────────────────────────────────────────┤
│          │ ExecutiveSummary (main content)                  │
│          │ ┌────────────────────────────────────────────┐   │
│          │ │ KpiStrip (8 key metrics)                   │   │
│          │ ├────────────────────────────────────────────┤   │
│          │ │ TrendCharts (performance trends)           │   │
│          │ ├────────────────────────────────────────────┤   │
│          │ │ Tabs: [Performance] [Pipeline] [Financial] │   │
│          │ │ [Strategic]                                │   │
│          │ ├────────────────────────────────────────────┤   │
│          │ │ PerformanceMetrics (detailed charts)       │   │
│          │ │ PipelineAnalysis (stage breakdown)         │   │
│          │ │ FinancialSummary (revenue/costs)           │   │
│          │ │ StrategicInsights (AI recommendations)     │   │
│          │ └────────────────────────────────────────────┘   │
├──────────┴──────────────────────────────────────────────────┤
│ AiDock (executive insights, strategic recommendations)      │
└─────────────────────────────────────────────────────────────┘
```

## Component Tree

```
ExecutiveSummaryPage
├── ExecutiveHeader
├── Breadcrumb
├── ExecutiveSummaryHeader
│   ├── CalendarRange (period)
│   ├── ChipSelect (agencies)
│   ├── ChipSelect (zones)
│   └── Button (Export Report)
├── ExecutiveSummary
│   ├── KpiStrip
│   │   ├── KpiCard (total_revenue)
│   │   ├── KpiCard (win_rate)
│   │   ├── KpiCard (total_bids)
│   │   ├── KpiCard (avg_bid_value)
│   │   ├── KpiCard (pipeline_value)
│   │   ├── KpiCard (conversion_rate)
│   │   ├── KpiCard (roi)
│   │   └── KpiCard (market_share)
│   ├── TrendCharts
│   │   ├── Chart (revenue_trend)
│   │   ├── Chart (win_rate_trend)
│   │   └── Chart (pipeline_trend)
│   ├── Tabs
│   │   ├── PerformanceTab
│   │   │   └── PerformanceMetrics
│   │   │       ├── Chart (by_agency)
│   │   │       ├── Chart (by_zone)
│   │   │       └── Table (detailed_metrics)
│   │   ├── PipelineTab
│   │   │   └── PipelineAnalysis
│   │   │       ├── Chart (stage_distribution)
│   │   │       ├── Chart (conversion_funnel)
│   │   │       └── Table (stage_details)
│   │   ├── FinancialTab
│   │   │   └── FinancialSummary
│   │   │       ├── Chart (revenue_vs_cost)
│   │   │       ├── Chart (margin_trend)
│   │   │       └── Table (financial_details)
│   │   └── StrategicTab
│   │       └── StrategicInsights
│   │           ├── AiInsight × N
│   │           │   ├── type
│   │           │   ├── title
│   │           │   ├── description
│   │           │   └── ConfidenceBadge
│   │           └── RecommendationList
│   └── ExecutiveActions
│       ├── Button (Generate Report)
│       ├── Button (Schedule Review)
│       └── Button (Share Summary)
└── AiDock
    ├── AgentCard (Executive Agent)
    └── EvidencePanel (executive insights)
```

## Data Sources

### Executive Summary
```typescript
// API: GET /api/v1/dashboard/executive
interface ExecutiveSummary {
  stats: ExecutiveStats;
  trends: ExecutiveTrend[];
  insights: ExecutiveInsight[];
}

interface ExecutiveStats {
  total_revenue: number;
  win_rate: number;
  total_bids: number;
  avg_bid_value: number;
  pipeline_value: number;
  conversion_rate: number;
  roi: number;
  market_share: number;
}

interface ExecutiveTrend {
  period: string;
  revenue: number;
  win_rate: number;
  pipeline_value: number;
}

interface ExecutiveInsight {
  insight_id: string;
  type: 'performance' | 'financial' | 'strategic';
  title: string;
  description: string;
  confidence: number;
  impact: 'high' | 'medium' | 'low';
}
```

### React Query
```typescript
const { data: summary } = useQuery({
  queryKey: ['dashboard', 'executive', period],
  queryFn: () => api.get('/api/v1/dashboard/executive', { params: period }),
  refetchInterval: 300_000, // 5 minutes
});
```

## Zustand Store
```typescript
// stores/executiveSummaryStore.ts
interface ExecutiveSummaryState {
  period: { start: string; end: string };
  setPeriod: (period: { start: string; end: string }) => void;
}
```

## Interactions

### Change Period
1. Select new period
2. Refetch summary
3. Update all metrics
4. Refresh charts

### View Details
1. Click KPI card
2. Open detail drawer
3. View breakdown
4. Analyze trends

### Export Report
1. Click Export button
2. Choose format
3. Include all sections
4. Download report

### View Insights
1. Click Strategic tab
2. Read AI insights
3. Review recommendations
4. Take action

## Responsive Breakpoints

| Breakpoint | Layout |
|------------|--------|
| Desktop (>1024px) | Full dashboard with tabs |
| Tablet (768-1024px) | Stacked tabs |
| Mobile (<768px) | Single tab view |

## Loading States
- KPIs: Skeleton cards
- Charts: Skeleton with shimmer
- Insights: Skeleton cards

## Error States
- Load failure: Retry button
- Export failure: Toast error
- Network error: Toast notification

## Accessibility
- KPIs announced via `aria-live`
- Charts have table fallback
- Screen reader: "Win rate: 45%, up 5%"
- Keyboard: Tab through elements

## Telemetry
- `executive_summary.view` — Screen loaded
- `executive_summary.period_change` — Period changed
- `executive_summary.export` — Report exported
- `executive_summary.insight_view` — Insight viewed

## Implementation Notes
- High-level KPI overview
- Trend charts for analysis
- AI-powered insights
- AiDock provides executive insights
- Export for board reporting
