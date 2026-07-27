# TEN-017: Bid History Screen Specification

**Module:** `features/bid-history/BidHistoryPage`
**Layer:** features
**Version:** 1.0.0
**Status:** Draft
**Workspace:** Acquisition

## Purpose
Historical bid tracking, performance analysis, and trend identification.

## Screen Layout

```
┌─────────────────────────────────────────────────────────────┐
│ ExecutiveHeader                                             │
├──────────┬──────────────────────────────────────────────────┤
│          │ Breadcrumb: Acquisition > Bid History             │
│ Workspace├──────────────────────────────────────────────────┤
│   Nav    │ BidHistoryHeader (period, filters)               │
│          ├──────────────────────────────────────────────────┤
│          │ BidHistory (main content)                        │
│          │ ┌────────────────────────────────────────────┐   │
│          │ │ KpiStrip (historical metrics)               │   │
│          │ ├────────────────────────────────────────────┤   │
│          │ │ Tabs: [Timeline] [Analytics] [Trends]      │   │
│          │ ├────────────────────────────────────────────┤   │
│          │ │ BidTimeline (chronological view)            │   │
│          │ │ BidAnalytics (performance metrics)          │   │
│          │ │ TrendAnalysis (historical patterns)         │   │
│          │ └────────────────────────────────────────────┘   │
├──────────┴──────────────────────────────────────────────────┤
│ AiDock (history insights, pattern analysis)                 │
└─────────────────────────────────────────────────────────────┘
```

## Component Tree

```
BidHistoryPage
├── ExecutiveHeader
├── Breadcrumb
├── BidHistoryHeader
│   ├── CalendarRange (period)
│   ├── ChipSelect (agencies)
│   ├── ChipSelect (status)
│   └── Button (Export History)
├── BidHistory
│   ├── KpiStrip
│   │   ├── KpiCard (total_bids)
│   │   ├── KpiCard (win_rate)
│   │   ├── KpiCard (avg_value)
│   │   └── KpiCard (total_value)
│   ├── Tabs
│   │   ├── TimelineTab
│   │   │   └── BidTimeline
│   │   │       └── TimelineItem × N
│   │   │           ├── date
│   │   │           ├── TenderCard (compact)
│   │   │           ├── status
│   │   │           ├── bid_value
│   │   │           └── result
│   │   ├── AnalyticsTab
│   │   │   └── BidAnalytics
│   │   │       ├── Chart (win_loss_ratio)
│   │   │       ├── Chart (by_agency)
│   │   │       ├── Chart (by_zone)
│   │   │       └── Table (detailed_metrics)
│   │   └── TrendsTab
│   │       └── TrendAnalysis
│   │           ├── Chart (bid_trends)
│   │           ├── Chart (value_trends)
│   │           ├── Chart (success_trends)
│   │           └── AiInsight × N
│   └── HistorySummary
│       ├── KpiCard (longest_win_streak)
│       ├── KpiCard (biggest_win)
│       └── KpiCard (avg_margin)
└── AiDock
    ├── AgentCard (Analytics Agent)
    └── EvidencePanel (history insights)
```

## Data Sources

### Bid History
```typescript
// API: GET /api/v1/pricing/history
interface BidHistory {
  bids: BidHistoryEntry[];
  stats: HistoryStats;
  trends: HistoryTrend[];
}

interface BidHistoryEntry {
  bid_id: string;
  tender_id: string;
  title: string;
  agency: string;
  zone: string;
  bid_value: number;
  estimated_value: number;
  status: 'won' | 'lost' | 'pending';
  submitted_at: string;
  result_at?: string;
  margin?: number;
}

interface HistoryStats {
  total_bids: number;
  wins: number;
  losses: number;
  win_rate: number;
  avg_bid_value: number;
  total_value: number;
  avg_margin: number;
  longest_win_streak: number;
  biggest_win: number;
}

interface HistoryTrend {
  period: string;
  bids: number;
  wins: number;
  value: number;
  win_rate: number;
}
```

### React Query
```typescript
const { data: history } = useQuery({
  queryKey: ['pricing', 'history', period],
  queryFn: () => api.get('/api/v1/pricing/history', { params: period }),
  refetchInterval: 300_000, // 5 minutes
});
```

## Zustand Store
```typescript
// stores/bidHistoryStore.ts
interface BidHistoryState {
  period: { start: string; end: string };
  setPeriod: (period: { start: string; end: string }) => void;
}
```

## Interactions

### View Timeline
1. Click Timeline tab
2. Scroll through bids
3. Click bid for details
4. View result

### Analyze Performance
1. Click Analytics tab
2. View charts
3. Analyze metrics
4. Identify patterns

### View Trends
1. Click Trends tab
2. View historical patterns
3. Read AI insights
4. Predict future

### Export History
1. Click Export button
2. Choose format
3. Include all details
4. Download file

## Responsive Breakpoints

| Breakpoint | Layout |
|------------|--------|
| Desktop (>1024px) | Full tabs with timeline |
| Tablet (768-1024px) | Stacked tabs |
| Mobile (<768px) | Single tab view |

## Loading States
- Timeline: Skeleton items
- Analytics: Skeleton charts
- Trends: Skeleton charts

## Error States
- Load failure: Retry button
- Export failure: Toast error
- Network error: Toast notification

## Accessibility
- Timeline items are focusable
- Metrics announced via `aria-live`
- Screen reader: "Win rate: 45%"
- Keyboard: Arrow keys to navigate

## Telemetry
- `bid_history.view` — Screen loaded
- `bid_history.tab_switch` — Tab changed
- `bid_history.bid_view` — Bid viewed
- `bid_history.export` — History exported

## Implementation Notes
- Chronological timeline view
- Performance analytics with charts
- Trend analysis with AI insights
- AiDock provides history insights
- Export for analysis
