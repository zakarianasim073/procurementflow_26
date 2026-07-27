# OPP-012: Tender Analytics Screen Specification

**Module:** `features/tender-analytics/TenderAnalyticsPage`
**Layer:** features
**Version:** 1.0.0
**Status:** Draft
**Workspace:** Opportunity

## Purpose
Analytics and insights for tender opportunities and market trends.

## Screen Layout

```
┌─────────────────────────────────────────────────────────────┐
│ ExecutiveHeader                                             │
├──────────┬──────────────────────────────────────────────────┤
│          │ Breadcrumb: Opportunity > Tender Analytics        │
│ Workspace├──────────────────────────────────────────────────┤
│   Nav    │ TenderAnalyticsHeader (insights, trends)         │
│          ├──────────────────────────────────────────────────┤
│          │ TenderAnalytics (main content)                   │
│          │ ┌────────────────────────────────────────────┐   │
│          │ │ KpiStrip (key metrics)                     │   │
│          │ ├────────────────────────────────────────────┤   │
│          │ │ Tabs: [Overview] [Trends] [Forecasting]    │   │
│          │ ├────────────────────────────────────────────┤   │
│          │ │ OverviewTab (summary charts)                │   │
│          │ │ TrendsTab (trend analysis)                  │   │
│          │ │ ForecastingTab (predictions)                │   │
│          │ └────────────────────────────────────────────┘   │
├──────────┴──────────────────────────────────────────────────┤
│ AiDock (analytics insights)                                 │
└─────────────────────────────────────────────────────────────┘
```

## Component Tree

```
TenderAnalyticsPage
├── ExecutiveHeader
├── Breadcrumb
├── TenderAnalyticsHeader
│   ├── KpiStrip (total_tenders, success_rate, avg_value)
│   └── Button (Export Analytics)
├── TenderAnalytics
│   ├── Tabs
│   │   ├── OverviewTab
│   │   │   ├── Chart (tender_distribution)
│   │   │   ├── Chart (agency_breakdown)
│   │   │   └── Chart (value_distribution)
│   │   ├── TrendsTab
│   │   │   ├── Chart (monthly_trends)
│   │   │   ├── Chart (seasonal_patterns)
│   │   │   └── Chart (market_growth)
│   │   └── ForecastingTab
│   │       ├── Chart (demand_forecast)
│   │       ├── Chart (price_forecast)
│   │       └── ForecastTable
│   │           └── ForecastItem × N
│   │               ├── category
│   │               ├── predicted_value
│   │               └── confidence
│   └── MarketInsights
│       ├── insight × N
│       │   ├── title
│       │   ├── description
│       │   └── impact
│       └── recommendations
└── AiDock
    ├── AgentCard (Analytics Agent)
    └── EvidencePanel (analytics insights)
```

## Data Sources

### Tender Analytics
```typescript
// API: GET /api/v1/opportunities/analytics
interface TenderAnalytics {
  overview: TenderOverview;
  trends: TenderTrends;
  forecast: TenderForecast;
}

interface TenderOverview {
  total_tenders: number;
  success_rate: number;
  avg_value: number;
  distribution: { category: string; count: number }[];
}

interface TenderTrends {
  monthly: { month: string; count: number; value: number }[];
  seasonal: { season: string; count: number }[];
  growth: { year: string; count: number }[];
}

interface TenderForecast {
  demand: { month: string; predicted: number; confidence: number }[];
  prices: { month: string; predicted: number; confidence: number }[];
}
```

### React Query
```typescript
const { data: analytics } = useQuery({
  queryKey: ['opportunities', 'analytics'],
  queryFn: () => api.get('/api/v1/opportunities/analytics'),
});
```

## Zustand Store
```typescript
// stores/tenderAnalyticsStore.ts
interface TenderAnalyticsState {
  activeTab: string;
  setTab: (tab: string) => void;
}
```

## Interactions

### View Overview
1. Click Overview tab
2. View charts
3. Analyze distribution
4. Check breakdown

### Analyze Trends
1. Click Trends tab
2. View monthly trends
3. Check seasonal patterns
4. Review growth

### View Forecast
1. Click Forecasting tab
2. View predictions
3. Check confidence
4. Read recommendations

### Export Analytics
1. Click Export
2. Choose format
3. Include all sections
4. Download report

## Responsive Breakpoints

| Breakpoint | Layout |
|------------|--------|
| Desktop (>1024px) | Full tabs + charts |
| Tablet (768-1024px) | Stacked tabs |
| Mobile (<768px) | Simplified view |

## Loading States
- Analytics: Loading charts
- Trends: Loading data
- Forecast: Loading predictions

## Error States
- Load failure: Retry button
- Export failure: Toast error
- Network error: Toast notification

## Accessibility
- Charts are keyboard navigable
- Metrics announced via `aria-live`
- Screen reader: "Total tenders: 1,234"
- Keyboard: Tab through charts

## Telemetry
- `tender_analytics.view` — Screen loaded
- `tender_analytics.export` — Analytics exported
- `tender_analytics.tab_change` — Tab changed

## Implementation Notes
- Comprehensive analytics
- Trend visualization
- Predictive forecasting
- AiDock provides analytics insights
- Export for analysis
