# TEN-023: Rate Analysis Dashboard Screen Specification

**Module:** `features/rate-analysis-dashboard/RateAnalysisDashboardPage`
**Layer:** features
**Version:** 1.0.0
**Status:** Draft
**Workspace:** Acquisition

## Purpose
Comprehensive rate analysis, comparisons, and optimization insights.

## Screen Layout

```
┌─────────────────────────────────────────────────────────────┐
│ ExecutiveHeader                                             │
├──────────┬──────────────────────────────────────────────────┤
│          │ Breadcrumb: Acquisition > Rate Analysis Dashboard │
│ Workspace├──────────────────────────────────────────────────┤
│   Nav    │ RateAnalysisDashboardHeader (insights, trends)   │
│          ├──────────────────────────────────────────────────┤
│          │ RateAnalysisDashboard (main content)             │
│          │ ┌────────────────────────────────────────────┐   │
│          │ │ KpiStrip (key metrics)                     │   │
│          │ ├────────────────────────────────────────────┤   │
│          │ │ Tabs: [Overview] [Trends] [Optimization]   │   │
│          │ ├────────────────────────────────────────────┤   │
│          │ │ OverviewTab (summary charts)                │   │
│          │ │ TrendsTab (trend analysis)                  │   │
│          │ │ OptimizationTab (optimization tips)         │   │
│          │ └────────────────────────────────────────────┘   │
├──────────┴──────────────────────────────────────────────────┤
│ AiDock (optimization insights)                              │
└─────────────────────────────────────────────────────────────┘
```

## Component Tree

```
RateAnalysisDashboardPage
├── ExecutiveHeader
├── Breadcrumb
├── RateAnalysisDashboardHeader
│   ├── KpiStrip (total_items, avg_rate, optimization_score)
│   └── Button (Export Report)
├── RateAnalysisDashboard
│   ├── Tabs
│   │   ├── OverviewTab
│   │   │   ├── Chart (rate_distribution)
│   │   │   ├── Chart (agency_comparison)
│   │   │   └── Chart (zone_analysis)
│   │   ├── TrendsTab
│   │   │   ├── Chart (rate_trends)
│   │   │   ├── Chart (volatility)
│   │   │   └── Chart (forecasting)
│   │   └── OptimizationTab
│   │       ├── OptimizationTip × N
│   │       │   ├── title
│   │       │   ├── description
│   │       │   ├── potential_saving
│   │       │   └── Button (Apply)
│   │       └── SavingsSummary
│   │           ├── total_potential
│   │           └── items_count
│   └── DetailedAnalysis
│       └── AnalysisTable
│           └── TableRow × N
│               ├── code
│               ├── description
│               ├── rates
│               └── variance
└── AiDock
    ├── AgentCard (Pricing Agent)
    └── EvidencePanel (optimization insights)
```

## Data Sources

### Rate Analysis
```typescript
// API: GET /api/v1/sor/analysis/dashboard
interface RateAnalysisDashboard {
  overview: RateOverview;
  trends: RateTrends;
  optimization: OptimizationTips;
}

interface RateOverview {
  total_items: number;
  avg_rate: number;
  optimization_score: number;
  rate_distribution: { range: string; count: number }[];
}

interface RateTrends {
  rate_trends: { date: string; avg_rate: number }[];
  volatility: number;
  forecast: { date: string; predicted_rate: number }[];
}

interface OptimizationTips {
  tips: OptimizationTip[];
  total_potential_saving: number;
}

interface OptimizationTip {
  tip_id: string;
  title: string;
  description: string;
  potential_saving: number;
  affected_items: string[];
}
```

### React Query
```typescript
const { data: dashboard } = useQuery({
  queryKey: ['sor', 'analysis', 'dashboard'],
  queryFn: () => api.get('/api/v1/sor/analysis/dashboard'),
});

const applyOptimization = useMutation({
  mutationFn: (tipId: string) => api.post(`/api/v1/sor/analysis/optimize/${tipId}`),
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ['sor', 'analysis', 'dashboard'] });
    toast.success('Optimization applied');
  },
});
```

## Zustand Store
```typescript
// stores/rateAnalysisDashboardStore.ts
interface RateAnalysisDashboardState {
  activeTab: string;
  setTab: (tab: string) => void;
}
```

## Interactions

### View Overview
1. Click Overview tab
2. View charts
3. Analyze distribution
4. Check agency comparison

### Analyze Trends
1. Click Trends tab
2. View trends
3. Check volatility
4. Review forecast

### Apply Optimization
1. Click Optimization tab
2. Review tips
3. Click Apply
4. Confirm optimization

### Export Report
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
- Dashboard: Loading charts
- Trends: Loading data
- Optimization: Loading tips

## Error States
- Load failure: Retry button
- Optimization failure: Toast error
- Network error: Toast notification

## Accessibility
- Charts are keyboard navigable
- Metrics announced via `aria-live`
- Screen reader: "Average rate: 150 BDT"
- Keyboard: Tab through charts

## Telemetry
- `rate_analysis_dashboard.view` — Screen loaded
- `rate_analysis_dashboard.optimize` — Optimization applied
- `rate_analysis_dashboard.export` — Report exported

## Implementation Notes
- Comprehensive rate analysis
- Trend visualization
- Optimization recommendations
- AiDock provides optimization insights
- Export for analysis
