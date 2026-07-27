# EXEC-018: Analytics Dashboard Screen Specification

**Module:** `features/analytics-dashboard/AnalyticsDashboardPage`
**Layer:** features
**Version:** 1.0.0
**Status:** Draft
**Workspace:** Dashboard

## Purpose
Comprehensive analytics, insights, and data visualization.

## Screen Layout

```
┌─────────────────────────────────────────────────────────────┐
│ ExecutiveHeader                                             │
├──────────┬──────────────────────────────────────────────────┤
│          │ Breadcrumb: Dashboard > Analytics Dashboard       │
│ Workspace├──────────────────────────────────────────────────┤
│   Nav    │ AnalyticsDashboardHeader (metrics, trends)       │
│          ├──────────────────────────────────────────────────┤
│          │ AnalyticsDashboard (main content)                │
│          │ ┌────────────────────────────────────────────┐   │
│          │ │ KpiStrip (key metrics)                     │   │
│          │ ├────────────────────────────────────────────┤   │
│          │ │ Tabs: [Overview] [Detailed] [Export]        │   │
│          │ ├────────────────────────────────────────────┤   │
│          │ │ OverviewTab (summary charts)                │   │
│          │ │ DetailedTab (detailed analysis)             │   │
│          │ │ ExportTab (export options)                   │   │
│          │ └────────────────────────────────────────────┘   │
├──────────┴──────────────────────────────────────────────────┤
│ AiDock (analytics insights)                                 │
└─────────────────────────────────────────────────────────────┘
```

## Component Tree

```
AnalyticsDashboardPage
├── ExecutiveHeader
├── Breadcrumb
├── AnalyticsDashboardHeader
│   ├── KpiStrip (total_tenders, success_rate, avg_value, growth)
│   └── Button (Export Report)
├── AnalyticsDashboard
│   ├── Tabs
│   │   ├── OverviewTab
│   │   │   ├── Chart (tender_trends)
│   │   │   ├── Chart (agency_breakdown)
│   │   │   ├── Chart (value_distribution)
│   │   │   └── Chart (success_rates)
│   │   ├── DetailedTab
│   │   │   ├── FilterBar
│   │   │   │   ├── ChipSelect (agency)
│   │   │   │   ├── ChipSelect (category)
│   │   │   │   └── CalendarRange (date_range)
│   │   │   ├── DetailedTable
│   │   │   │   └── TableRow × N
│   │   │   │       ├── tender_name
│   │   │   │       ├── agency
│   │   │   │       ├── value
│   │   │   │       ├── status
│   │   │   │       └── date
│   │   │   └── TrendAnalysis
│   │   └── ExportTab
│   │       ├── ExportOptions
│   │       │   └── ExportType × N
│   │       │       ├── name
│   │       │       ├── format
│   │       │       └── Button (Export)
│   │       └── ExportHistory
│   │           └── ExportEntry × N
│   │               ├── date
│   │               ├── type
│   │               └── Button (Download)
│   └── InsightsPanel
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

### Analytics Data
```typescript
// API: GET /api/v1/reports/analytics
interface AnalyticsData {
  overview: AnalyticsOverview;
  detailed: DetailedAnalytics;
  insights: AnalyticsInsight[];
}

interface AnalyticsOverview {
  total_tenders: number;
  success_rate: number;
  avg_value: number;
  growth: number;
  trends: { date: string; count: number; value: number }[];
}

interface DetailedAnalytics {
  tenders: TenderAnalytics[];
  agencies: AgencyAnalytics[];
  categories: CategoryAnalytics[];
}

interface AnalyticsInsight {
  insight_id: string;
  title: string;
  description: string;
  impact: 'positive' | 'negative' | 'neutral';
  recommendation: string;
}
```

### React Query
```typescript
const { data: analytics } = useQuery({
  queryKey: ['reports', 'analytics'],
  queryFn: () => api.get('/api/v1/reports/analytics'),
});
```

## Zustand Store
```typescript
// stores/analyticsDashboardStore.ts
interface AnalyticsDashboardState {
  activeTab: string;
  filters: {
    agency: string[];
    category: string[];
    dateRange: { start: string; end: string } | null;
  };
  setTab: (tab: string) => void;
  setFilter: <K extends keyof AnalyticsDashboardState['filters']>(key: K, value: AnalyticsDashboardState['filters'][K]) => void;
}
```

## Interactions

### View Overview
1. Click Overview tab
2. View charts
3. Analyze trends
4. Check breakdown

### View Detailed
1. Click Detailed tab
2. Apply filters
3. View table
4. Analyze trends

### Export Report
1. Click Export tab
2. Choose format
3. Select data
4. Download report

### View Insights
1. Read insights
2. Check impact
3. Follow recommendations
4. Take action

## Responsive Breakpoints

| Breakpoint | Layout |
|------------|--------|
| Desktop (>1024px) | Full tabs + charts |
| Tablet (768-1024px) | Stacked tabs |
| Mobile (<768px) | Simplified view |

## Loading States
- Analytics: Loading charts
- Detailed: Loading table
- Export: Loading options

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
- `analytics_dashboard.view` — Screen loaded
- `analytics_dashboard.tab_change` — Tab changed
- `analytics_dashboard.export` — Report exported
- `analytics_dashboard.filter` — Filter applied

## Implementation Notes
- Comprehensive analytics
- Detailed analysis
- Export functionality
- AiDock provides analytics insights
- Interactive charts
