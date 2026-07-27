# TEN-024: Cost Analysis Screen Specification

**Module:** `features/cost-analysis/CostAnalysisPage`
**Layer:** features
**Version:** 1.0.0
**Status:** Draft
**Workspace:** Acquisition

## Purpose
Comprehensive cost analysis, budgeting, and financial planning.

## Screen Layout

```
┌─────────────────────────────────────────────────────────────┐
│ ExecutiveHeader                                             │
├──────────┬──────────────────────────────────────────────────┤
│          │ Breadcrumb: Acquisition > Cost Analysis           │
│ Workspace├──────────────────────────────────────────────────┤
│   Nav    │ CostAnalysisHeader (budget, variance)            │
│          ├──────────────────────────────────────────────────┤
│          │ CostAnalysis (main content)                      │
│          │ ┌────────────────────────────────────────────┐   │
│          │ │ KpiStrip (key metrics)                     │   │
│          │ ├────────────────────────────────────────────┤   │
│          │ │ Tabs: [Overview] [Budget] [Forecasting]    │   │
│          │ ├────────────────────────────────────────────┤   │
│          │ │ OverviewTab (summary charts)                │   │
│          │ │ BudgetTab (budget tracking)                 │   │
│          │ │ ForecastingTab (predictions)                │   │
│          │ └────────────────────────────────────────────┘   │
├──────────┴──────────────────────────────────────────────────┤
│ AiDock (cost insights)                                      │
└─────────────────────────────────────────────────────────────┘
```

## Component Tree

```
CostAnalysisPage
├── ExecutiveHeader
├── Breadcrumb
├── CostAnalysisHeader
│   ├── KpiStrip (total_budget, spent, remaining, variance)
│   └── Button (Export Report)
├── CostAnalysis
│   ├── Tabs
│   │   ├── OverviewTab
│   │   │   ├── Chart (cost_distribution)
│   │   │   ├── Chart (cost_by_category)
│   │   │   └── Chart (trend_analysis)
│   │   ├── BudgetTab
│   │   │   ├── BudgetProgress
│   │   │   │   ├── category
│   │   │   │   ├── allocated
│   │   │   │   ├── spent
│   │   │   │   └── remaining
│   │   │   └── VarianceReport
│   │   │       └── VarianceItem × N
│   │   │           ├── category
│   │   │           ├── budgeted
│   │   │           ├── actual
│   │   │           └── variance
│   │   └── ForecastingTab
│   │       ├── Chart (cost_forecast)
│   │       ├── Chart (scenario_analysis)
│   │       └── ForecastTable
│   │           └── ForecastItem × N
│   │               ├── period
│   │               ├── predicted
│   │               └── confidence
│   └── CostBreakdown
│       └── BreakdownTable
│           └── BreakdownRow × N
│               ├── item
│               ├── quantity
│               ├── rate
│               └── total
└── AiDock
    ├── AgentCard (Pricing Agent)
    └── EvidencePanel (cost insights)
```

## Data Sources

### Cost Analysis
```typescript
// API: GET /api/v1/sor/cost-analysis
interface CostAnalysis {
  overview: CostOverview;
  budget: BudgetData;
  forecast: CostForecast;
}

interface CostOverview {
  total_budget: number;
  spent: number;
  remaining: number;
  variance: number;
  distribution: { category: string; amount: number }[];
}

interface BudgetData {
  categories: BudgetCategory[];
  variances: VarianceItem[];
}

interface BudgetCategory {
  category: string;
  allocated: number;
  spent: number;
  remaining: number;
}

interface VarianceItem {
  category: string;
  budgeted: number;
  actual: number;
  variance: number;
  percentage: number;
}

interface CostForecast {
  periods: ForecastPeriod[];
  scenarios: ScenarioAnalysis[];
}

interface ForecastPeriod {
  period: string;
  predicted: number;
  confidence: number;
  lower_bound: number;
  upper_bound: number;
}
```

### React Query
```typescript
const { data: analysis } = useQuery({
  queryKey: ['sor', 'cost-analysis'],
  queryFn: () => api.get('/api/v1/sor/cost-analysis'),
});

const updateBudget = useMutation({
  mutationFn: (budget: UpdateBudgetRequest) => api.put('/api/v1/sor/cost-analysis/budget', budget),
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ['sor', 'cost-analysis'] });
    toast.success('Budget updated');
  },
});
```

## Zustand Store
```typescript
// stores/costAnalysisStore.ts
interface CostAnalysisState {
  activeTab: string;
  setTab: (tab: string) => void;
}
```

## Interactions

### View Overview
1. Click Overview tab
2. View charts
3. Analyze distribution
4. Check trends

### Track Budget
1. Click Budget tab
2. View progress
3. Check variances
4. Update allocations

### View Forecast
1. Click Forecasting tab
2. View predictions
3. Check scenarios
4. Read confidence

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
- Analysis: Loading charts
- Budget: Loading data
- Forecast: Loading predictions

## Error States
- Load failure: Retry button
- Update failure: Toast error
- Network error: Toast notification

## Accessibility
- Charts are keyboard navigable
- Metrics announced via `aria-live`
- Screen reader: "Budget spent: 75%"
- Keyboard: Tab through charts

## Telemetry
- `cost_analysis.view` — Screen loaded
- `cost_analysis.budget_update` — Budget updated
- `cost_analysis.export` — Report exported

## Implementation Notes
- Comprehensive cost analysis
- Budget tracking
- Predictive forecasting
- AiDock provides cost insights
- Export for analysis
