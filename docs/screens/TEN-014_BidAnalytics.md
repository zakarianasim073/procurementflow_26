# TEN-014: Bid Analytics Screen Specification

**Module:** `features/bid-analytics/BidAnalyticsPage`
**Layer:** features
**Version:** 1.0.0
**Status:** Draft
**Workspace:** Acquisition

## Purpose
Bid performance analytics, win/loss analysis, and optimization insights.

## Screen Layout

```
┌─────────────────────────────────────────────────────────────┐
│ ExecutiveHeader                                             │
├──────────┬──────────────────────────────────────────────────┤
│          │ Breadcrumb: Acquisition > Bid Analytics           │
│ Workspace├──────────────────────────────────────────────────┤
│   Nav    │ BidAnalyticsHeader (period, filters)             │
│          ├──────────────────────────────────────────────────┤
│          │ BidAnalytics (main content)                      │
│          │ ┌────────────────────────────────────────────┐   │
│          │ │ KpiStrip (bid metrics)                      │   │
│          │ ├────────────────────────────────────────────┤   │
│          │ │ Tabs: [Performance] [Win/Loss] [Trends]    │   │
│          │ │ [Optimization]                              │   │
│          │ ├────────────────────────────────────────────┤   │
│          │ │ BidPerformance (success metrics)            │   │
│          │ │ WinLossAnalysis (outcome breakdown)         │   │
│          │ │ TrendAnalysis (historical patterns)         │   │
│          │ │ OptimizationPanel (AI recommendations)      │   │
│          │ └────────────────────────────────────────────┘   │
├──────────┴──────────────────────────────────────────────────┤
│ AiDock (bid insights, optimization)                         │
└─────────────────────────────────────────────────────────────┘
```

## Component Tree

```
BidAnalyticsPage
├── ExecutiveHeader
├── Breadcrumb
├── BidAnalyticsHeader
│   ├── CalendarRange (period)
│   ├── ChipSelect (agencies)
│   ├── ChipSelect (zones)
│   └── Button (Export Report)
├── BidAnalytics
│   ├── KpiStrip
│   │   ├── KpiCard (total_bids)
│   │   ├── KpiCard (win_rate)
│   │   ├── KpiCard (avg_bid_value)
│   │   └── KpiCard (total_value)
│   ├── Tabs
│   │   ├── PerformanceTab
│   │   │   └── BidPerformance
│   │   │       ├── Chart (success_rate)
│   │   │       ├── Chart (by_agency)
│   │   │       └── Table (detailed_metrics)
│   │   ├── WinLossTab
│   │   │   └── WinLossAnalysis
│   │   │       ├── Chart (win_loss_ratio)
│   │   │       ├── Chart (by_reason)
│   │   │       └── Table (loss_analysis)
│   │   ├── TrendsTab
│   │   │   └── TrendAnalysis
│   │   │       ├── Chart (bid_trends)
│   │   │       ├── Chart (value_trends)
│   │   │       └── AiInsight × N
│   │   └── OptimizationTab
│   │       └── OptimizationPanel
│   │           ├── Recommendation × N
│   │           │   ├── type
│   │           │   ├── description
│   │           │   └── Button (Apply)
│   │           └── ConfidenceBadge
│   └── BidSummary
│       ├── KpiCard (conversion_rate)
│       ├── KpiCard (avg_margin)
│       └── KpiCard (roi)
└── AiDock
    ├── AgentCard (Pricing Agent)
    └── EvidencePanel (bid insights)
```

## Data Sources

### Bid Analytics
```typescript
// API: GET /api/v1/pricing/analytics
interface BidAnalytics {
  stats: BidStats;
  win_loss: WinLossData;
  trends: BidTrend[];
  recommendations: BidRecommendation[];
}

interface BidStats {
  total_bids: number;
  win_rate: number;
  avg_bid_value: number;
  total_value: number;
  conversion_rate: number;
  avg_margin: number;
  roi: number;
}

interface WinLossData {
  wins: number;
  losses: number;
  pending: number;
  reasons: { reason: string; count: number }[];
}

interface BidTrend {
  period: string;
  bids: number;
  wins: number;
  value: number;
}

interface BidRecommendation {
  type: string;
  description: string;
  impact: number;
  confidence: number;
}
```

### React Query
```typescript
const { data: analytics } = useQuery({
  queryKey: ['pricing', 'analytics', period],
  queryFn: () => api.get('/api/v1/pricing/analytics', { params: period }),
  refetchInterval: 300_000, // 5 minutes
});
```

## Zustand Store
```typescript
// stores/bidAnalyticsStore.ts
interface BidAnalyticsState {
  period: { start: string; end: string };
  setPeriod: (period: { start: string; end: string }) => void;
}
```

## Interactions

### View Performance
1. Click Performance tab
2. View success metrics
3. Analyze by agency
4. Review details

### Analyze Win/Loss
1. Click Win/Loss tab
2. View ratio chart
3. Analyze reasons
4. Identify patterns

### View Trends
1. Click Trends tab
2. View historical patterns
3. Read AI insights
4. Identify opportunities

### Apply Optimization
1. Click Optimization tab
2. View recommendations
3. Click Apply
4. Confirm action

## Responsive Breakpoints

| Breakpoint | Layout |
|------------|--------|
| Desktop (>1024px) | Full tabs with charts |
| Tablet (768-1024px) | Stacked tabs |
| Mobile (<768px) | Single tab view |

## Loading States
- KPIs: Skeleton cards
- Charts: Skeleton with shimmer
- Recommendations: Skeleton cards

## Error States
- Load failure: Retry button
- Apply failure: Toast error
- Network error: Toast notification

## Accessibility
- KPIs announced via `aria-live`
- Charts have table fallback
- Screen reader: "Win rate: 45%"
- Keyboard: Tab through elements

## Telemetry
- `bid_analytics.view` — Screen loaded
- `bid_analytics.tab_switch` — Tab changed
- `bid_analytics.optimize` — Recommendation applied
- `bid_analytics.export` — Report exported

## Implementation Notes
- KPI overview with metrics
- Win/loss analysis
- Historical trend analysis
- AiDock provides bid insights
- Export for reporting
