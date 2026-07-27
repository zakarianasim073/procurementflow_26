# KNOW-009: Market Trends Screen Specification

**Module:** `features/market-trends/MarketTrendsPage`
**Layer:** features
**Version:** 1.0.0
**Status:** Draft
**Workspace:** Knowledge

## Purpose
Market trend analysis, price forecasting, and competitive intelligence.

## Screen Layout

```
┌─────────────────────────────────────────────────────────────┐
│ ExecutiveHeader                                             │
├──────────┬──────────────────────────────────────────────────┤
│          │ Breadcrumb: Knowledge > Market Trends             │
│ Workspace├──────────────────────────────────────────────────┤
│   Nav    │ MarketTrendsHeader (date range, filters)         │
│          ├──────────────────────────────────────────────────┤
│          │ MarketTrends (main content)                      │
│          │ ┌────────────────────────────────────────────┐   │
│          │ │ Tabs: [Overview] [Forecasts] [Competitors] │   │
│          │ │ [Zones]                                     │   │
│          │ ├────────────────────────────────────────────┤   │
│          │ │ TrendOverview (summary charts)              │   │
│          │ │ ForecastPanel (price predictions)           │   │
│          │ │ CompetitorTrends (bid patterns)             │   │
│          │ │ ZoneTrends (geographic analysis)            │   │
│          │ └────────────────────────────────────────────┘   │
├──────────┴──────────────────────────────────────────────────┤
│ AiDock (trend insights, forecasting)                        │
└─────────────────────────────────────────────────────────────┘
```

## Component Tree

```
MarketTrendsPage
├── ExecutiveHeader
├── Breadcrumb
├── MarketTrendsHeader
│   ├── CalendarRange (date range)
│   ├── ChipSelect (agencies)
│   ├── ChipSelect (zones)
│   └── Button (Export Report)
├── MarketTrends
│   ├── Tabs
│   │   ├── OverviewTab
│   │   │   └── TrendOverview
│   │   │       ├── Chart (price_trends)
│   │   │       ├── Chart (volume_trends)
│   │   │       └── KpiStrip (metrics)
│   │   ├── ForecastsTab
│   │   │   └── ForecastPanel
│   │   │       ├── Chart (price_forecast)
│   │   │       ├── Chart (demand_forecast)
│   │   │       └── ConfidenceBadge
│   │   ├── CompetitorsTab
│   │   │   └── CompetitorTrends
│   │   │       ├── Chart (bid_patterns)
│   │   │       ├── Chart (win_rates)
│   │   │       └── CompetitorCard × N
│   │   └── ZonesTab
│   │       └── ZoneTrends
│   │           ├── Heatmap (zone_activity)
│   │           ├── Chart (zone_comparison)
│   │           └── ZoneCard × N
│   └── TrendSummary
│       ├── KpiCard (avg_price)
│       ├── KpiCard (price_change)
│       └── KpiCard (volatility)
└── AiDock
    ├── AgentCard (Intelligence Agent)
    └── EvidencePanel (trend insights)
```

## Data Sources

### Market Trends
```typescript
// API: GET /api/v1/knowledge/market/trends
interface MarketTrends {
  price_trends: TrendData[];
  volume_trends: TrendData[];
  forecasts: ForecastData[];
}

interface TrendData {
  period: string;
  value: number;
  change_pct: number;
  trend: 'rising' | 'stable' | 'falling';
}

interface ForecastData {
  period: string;
  predicted: number;
  confidence: number;
  range: { min: number; max: number };
}
```

### Competitor Trends
```typescript
// API: GET /api/v1/knowledge/market/competitor-trends
interface CompetitorTrends {
  competitors: CompetitorTrend[];
  bid_patterns: BidPattern[];
}

interface CompetitorTrend {
  competitor_id: string;
  name: string;
  avg_bid_ratio: number;
  win_rate: number;
  trend: 'increasing' | 'stable' | 'decreasing';
}

interface BidPattern {
  pattern: string;
  frequency: number;
  description: string;
}
```

### React Query
```typescript
const { data: trends } = useQuery({
  queryKey: ['knowledge', 'market', 'trends', dateRange],
  queryFn: () => api.get('/api/v1/knowledge/market/trends', { params: dateRange }),
});

const { data: competitorTrends } = useQuery({
  queryKey: ['knowledge', 'market', 'competitor-trends'],
  queryFn: () => api.get('/api/v1/knowledge/market/competitor-trends'),
});
```

## Zustand Store
```typescript
// stores/marketTrendsStore.ts
interface MarketTrendsState {
  dateRange: { start: string; end: string };
  setRange: (range: { start: string; end: string }) => void;
}
```

## Interactions

### View Overview
1. Click Overview tab
2. View price trends
3. Analyze volume
4. Review metrics

### View Forecasts
1. Click Forecasts tab
2. View predictions
3. Analyze confidence
4. Review ranges

### Analyze Competitors
1. Click Competitors tab
2. View bid patterns
3. Compare win rates
4. Identify opportunities

### Explore Zones
1. Click Zones tab
2. View zone heatmap
3. Compare zones
4. Identify hotspots

## Responsive Breakpoints

| Breakpoint | Layout |
|------------|--------|
| Desktop (>1024px) | Full tabs with charts |
| Tablet (768-1024px) | Stacked tabs |
| Mobile (<768px) | Single tab view |

## Loading States
- Charts: Skeleton with shimmer
- Forecasts: Skeleton chart
- Competitors: Skeleton cards

## Error States
- Load failure: Retry button
- No data: EmptyState
- Network error: Toast notification

## Accessibility
- Charts have table fallback
- Trends announced via `aria-live`
- Screen reader: "Price trend: rising 5%"
- Keyboard: Tab through elements

## Telemetry
- `market_trends.view` — Screen loaded
- `market_trends.tab_switch` — Tab changed
- `market_trends.export` — Report exported

## Implementation Notes
- 4 tabs for different analysis
- Charts for visualization
- AI-powered forecasts
- AiDock provides trend insights
- Export for strategic planning
