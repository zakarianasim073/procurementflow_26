# OPP-013: Market Trends Screen Specification

**Module:** `features/market-trends/MarketTrendsPage`
**Layer:** features
**Version:** 1.0.0
**Status:** Draft
**Workspace:** Opportunity

## Purpose
Track market trends, industry insights, and competitive intelligence.

## Screen Layout

```
┌─────────────────────────────────────────────────────────────┐
│ ExecutiveHeader                                             │
├──────────┬──────────────────────────────────────────────────┤
│          │ Breadcrumb: Opportunity > Market Trends           │
│ Workspace├──────────────────────────────────────────────────┤
│   Nav    │ MarketTrendsHeader (trends, insights)            │
│          ├──────────────────────────────────────────────────┤
│          │ MarketTrends (main content)                      │
│          │ ┌────────────────────────────────────────────┐   │
│          │ │ TrendOverview (summary)                     │   │
│          │ ├────────────────────────────────────────────┤   │
│          │ │ Tabs: [Trends] [Insights] [Forecasting]    │   │
│          │ ├────────────────────────────────────────────┤   │
│          │ │ TrendsTab (trend charts)                    │   │
│          │ │ InsightsTab (market insights)               │   │
│          │ │ ForecastingTab (predictions)                │   │
│          │ └────────────────────────────────────────────┘   │
├──────────┴──────────────────────────────────────────────────┤
│ AiDock (market intelligence)                                │
└─────────────────────────────────────────────────────────────┘
```

## Component Tree

```
MarketTrendsPage
├── ExecutiveHeader
├── Breadcrumb
├── MarketTrendsHeader
│   ├── KpiStrip (trend_score, growth_rate, market_size)
│   └── Button (Export Insights)
├── MarketTrends
│   ├── TrendOverview
│   │   ├── Chart (market_growth)
│   │   ├── Chart (trend_indicators)
│   │   └── Chart (competitive_landscape)
│   ├── Tabs
│   │   ├── TrendsTab
│   │   │   └── TrendList
│   │   │       └── TrendCard × N
│   │   │           ├── name
│   │   │           ├── direction
│   │   │           ├── impact
│   │   │           └── Button (Details)
│   │   ├── InsightsTab
│   │   │   └── InsightList
│   │   │       └── InsightCard × N
│   │   │           ├── title
│   │   │           ├── summary
│   │   │           ├── source
│   │   │           └── Button (Read More)
│   │   └── ForecastingTab
│   │       └── ForecastList
│   │           └── ForecastCard × N
│   │               ├── category
│   │               ├── prediction
│   │               ├── confidence
│   │               └── trend
│   └── MarketReport
│       ├── executive_summary
│       ├── key_findings
│       └── recommendations
└── AiDock
    ├── AgentCard (Intelligence Agent)
    └── EvidencePanel (market insights)
```

## Data Sources

### Market Trends
```typescript
// API: GET /api/v1/opportunities/market-trends
interface MarketTrends {
  overview: TrendOverview;
  trends: Trend[];
  insights: MarketInsight[];
  forecast: MarketForecast[];
}

interface TrendOverview {
  trend_score: number;
  growth_rate: number;
  market_size: number;
  indicators: { name: string; value: number; trend: string }[];
}

interface Trend {
  trend_id: string;
  name: string;
  direction: 'up' | 'down' | 'stable';
  impact: 'high' | 'medium' | 'low';
  description: string;
  data_points: { date: string; value: number }[];
}

interface MarketInsight {
  insight_id: string;
  title: string;
  summary: string;
  source: string;
  published_at: string;
  relevance: number;
}

interface MarketForecast {
  category: string;
  prediction: number;
  confidence: number;
  trend: 'growing' | 'declining' | 'stable';
}
```

### React Query
```typescript
const { data: trends } = useQuery({
  queryKey: ['opportunities', 'market-trends'],
  queryFn: () => api.get('/api/v1/opportunities/market-trends'),
});
```

## Zustand Store
```typescript
// stores/marketTrendsStore.ts
interface MarketTrendsState {
  activeTab: string;
  setTab: (tab: string) => void;
}
```

## Interactions

### View Trends
1. Click Trends tab
2. View trend cards
3. Check direction
4. Analyze impact

### Read Insights
1. Click Insights tab
2. View insights
3. Read summaries
4. Check sources

### View Forecast
1. Click Forecasting tab
2. View predictions
3. Check confidence
4. Analyze trends

### Export Insights
1. Click Export
2. Choose format
3. Include all data
4. Download report

## Responsive Breakpoints

| Breakpoint | Layout |
|------------|--------|
| Desktop (>1024px) | Full tabs + charts |
| Tablet (768-1024px) | Stacked tabs |
| Mobile (<768px) | Simplified view |

## Loading States
- Trends: Loading charts
- Insights: Loading cards
- Forecast: Loading predictions

## Error States
- Load failure: Retry button
- Export failure: Toast error
- Network error: Toast notification

## Accessibility
- Trends are focusable
- Insights announced via `aria-live`
- Screen reader: "Trend: Infrastructure growth, direction: up"
- Keyboard: Tab through trends

## Telemetry
- `market_trends.view` — Screen loaded
- `market_trends.trend_view` — Trend viewed
- `market_trends.insight_read` — Insight read
- `market_trends.export` — Insights exported

## Implementation Notes
- Market trend tracking
- Insight aggregation
- Predictive forecasting
- AiDock provides market intelligence
- Export for analysis
