# TEN-012: Pricing Strategy Dashboard Screen Specification

**Module:** `features/pricing-dashboard/PricingDashboardPage`
**Layer:** features
**Version:** 1.0.0
**Status:** Draft
**Workspace:** Acquisition

## Purpose
Overview of pricing strategies, bid analytics, and optimization recommendations.

## Screen Layout

```
┌─────────────────────────────────────────────────────────────┐
│ ExecutiveHeader                                             │
├──────────┬──────────────────────────────────────────────────┤
│          │ Breadcrumb: Acquisition > Pricing Dashboard       │
│ Workspace├──────────────────────────────────────────────────┤
│   Nav    │ PricingDashboardHeader (stats, trends)           │
│          ├──────────────────────────────────────────────────┤
│          │ PricingDashboard (main content)                  │
│          │ ┌────────────────────────────────────────────┐   │
│          │ │ KpiStrip (pricing metrics)                  │   │
│          │ ├────────────────────────────────────────────┤   │
│          │ │ Tabs: [Overview] [Trends] [Optimization]   │   │
│          │ │ [Recommendations]                           │   │
│          │ ├────────────────────────────────────────────┤   │
│          │ │ PricingOverview (summary charts)            │   │
│          │ │ TrendAnalysis (price trends)                │   │
│          │ │ OptimizationPanel (AI suggestions)          │   │
│          │ │ RecommendationList (action items)           │   │
│          │ └────────────────────────────────────────────┘   │
├──────────┴──────────────────────────────────────────────────┤
│ AiDock (pricing insights, optimization)                     │
└─────────────────────────────────────────────────────────────┘
```

## Component Tree

```
PricingDashboardPage
├── ExecutiveHeader
├── Breadcrumb
├── PricingDashboardHeader
│   ├── KpiStrip (total_bids, avg_margin, win_rate, total_value)
│   └── Button (Export Report)
├── PricingDashboard
│   ├── Tabs
│   │   ├── OverviewTab
│   │   │   └── PricingOverview
│   │   │       ├── Chart (bids_over_time)
│   │   │       ├── Chart (margin_distribution)
│   │   │       └── KpiStrip (detailed_metrics)
│   │   ├── TrendsTab
│   │   │   └── TrendAnalysis
│   │   │       ├── Chart (price_trends)
│   │   │       ├── Chart (competitor_trends)
│   │   │       └── AiInsight × N
│   │   ├── OptimizationTab
│   │   │   └── OptimizationPanel
│   │   │       ├── Recommendation × N
│   │   │       │   ├── type
│   │   │       │   ├── description
│   │   │       │   ├── impact
│   │   │       │   └── Button (Apply)
│   │   │       └── ConfidenceBadge
│   │   └── RecommendationsTab
│   │       └── RecommendationList
│   │           └── RecommendationCard × N
│   │               ├── title
│   │               ├── description
│   │               ├── priority
│   │               └── Button (Implement)
│   └── PricingSummary
│       ├── KpiCard (total_bids)
│       ├── KpiCard (avg_margin)
│       └── KpiCard (optimization_score)
└── AiDock
    ├── AgentCard (Pricing Agent)
    └── EvidencePanel (pricing insights)
```

## Data Sources

### Pricing Dashboard
```typescript
// API: GET /api/v1/pricing/dashboard
interface PricingDashboard {
  stats: PricingStats;
  trends: PricingTrend[];
  recommendations: PricingRecommendation[];
}

interface PricingStats {
  total_bids: number;
  avg_margin: number;
  win_rate: number;
  total_value: number;
  optimization_score: number;
}

interface PricingTrend {
  period: string;
  avg_price: number;
  avg_margin: number;
  bid_count: number;
}

interface PricingRecommendation {
  recommendation_id: string;
  type: 'price' | 'margin' | 'strategy';
  title: string;
  description: string;
  impact: number;
  confidence: number;
  priority: 'high' | 'medium' | 'low';
}
```

### React Query
```typescript
const { data: dashboard } = useQuery({
  queryKey: ['pricing', 'dashboard'],
  queryFn: () => api.get('/api/v1/pricing/dashboard'),
  refetchInterval: 60_000, // 1 minute
});

const applyRecommendation = useMutation({
  mutationFn: (request: ApplyRecommendationRequest) =>
    api.post('/api/v1/pricing/recommendations/apply', request),
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ['pricing', 'dashboard'] });
    toast.success('Recommendation applied');
  },
});
```

## Zustand Store
```typescript
// stores/pricingDashboardStore.ts
interface PricingDashboardState {
  activeTab: string;
  setTab: (tab: string) => void;
}
```

## Interactions

### View Overview
1. Click Overview tab
2. View summary charts
3. Analyze metrics
4. Review trends

### Analyze Trends
1. Click Trends tab
2. View price trends
3. Compare competitor trends
4. Read AI insights

### Apply Optimization
1. Click Optimization tab
2. View recommendations
3. Click Apply button
4. Confirm action

### Implement Recommendation
1. Click Recommendations tab
2. View recommendation cards
3. Click Implement
4. Execute action

## Responsive Breakpoints

| Breakpoint | Layout |
|------------|--------|
| Desktop (>1024px) | Full tabs with charts |
| Tablet (768-1024px) | Stacked tabs |
| Mobile (<768px) | Single tab view |

## Loading States
- Charts: Skeleton with shimmer
- Recommendations: Skeleton cards
- KPIs: Skeleton cards

## Error States
- Load failure: Retry button
- Apply failure: Toast error
- Network error: Toast notification

## Accessibility
- Charts have table fallback
- Recommendations are focusable
- Screen reader: "Win rate: 45%"
- Keyboard: Tab through elements

## Telemetry
- `pricing_dashboard.view` — Screen loaded
- `pricing_dashboard.tab_switch` — Tab changed
- `pricing_dashboard.optimize` — Recommendation applied
- `pricing_dashboard.export` — Report exported

## Implementation Notes
- Overview with summary charts
- Trend analysis with AI insights
- Optimization panel with recommendations
- AiDock provides pricing insights
- Export for reporting
