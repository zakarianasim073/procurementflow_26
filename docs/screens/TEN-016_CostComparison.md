# TEN-016: Cost Comparison Screen Specification

**Module:** `features/cost-comparison/CostComparisonPage`
**Layer:** features
**Version:** 1.0.0
**Status:** Draft
**Workspace:** Acquisition

## Purpose
Side-by-side cost comparison, variance analysis, and optimization.

## Screen Layout

```
┌─────────────────────────────────────────────────────────────┐
│ ExecutiveHeader                                             │
├──────────┬──────────────────────────────────────────────────┤
│          │ Breadcrumb: Acquisition > Cost Comparison         │
│ Workspace├──────────────────────────────────────────────────┤
│   Nav    │ CostComparisonHeader (tender context)            │
│          ├──────────────────────────────────────────────────┤
│          │ CostComparison (main content)                    │
│          │ ┌────────────────────────────────────────────┐   │
│          │ │ ComparisonTable (side-by-side)              │   │
│          │ │ ┌──────────┬──────────┬──────────┐          │   │
│          │ │ │ Our Bid  │ SOR Rate │ Market   │          │   │
│          │ │ │ 50M      │ 48M      │ 52M      │          │   │
│          │ │ ├──────────┼──────────┼──────────┤          │   │
│          │ │ │ Items    │ Items    │ Items    │          │   │
│          │ │ │ Rates    │ Rates    │ Rates    │          │   │
│          │ │ │ Variance │ Variance │ Variance │          │   │
│          │ │ └──────────┴──────────┴──────────┘          │   │
│          │ ├────────────────────────────────────────────┤   │
│          │ │ VarianceAnalysis (differences)              │   │
│          │ └────────────────────────────────────────────┘   │
├──────────┴──────────────────────────────────────────────────┤
│ AiDock (cost insights, optimization)                        │
└─────────────────────────────────────────────────────────────┘
```

## Component Tree

```
CostComparisonPage
├── ExecutiveHeader
├── Breadcrumb
├── CostComparisonHeader
│   ├── TenderCard (compact)
│   └── KpiStrip (total_cost, variance, optimization_score)
├── CostComparison
│   ├── ComparisonTable
│   │   └── Table<CostComparison>
│   │       ├── category
│   │       ├── our_bid
│   │       ├── sor_rate
│   │       ├── market_rate
│   │       └── variance
│   ├── ItemBreakdown
│   │   └── Table<ItemComparison>
│   │       ├── item_code
│   │       ├── our_rate
│   │       ├── sor_rate
│   │       ├── market_rate
│   │       └── variance
│   └── VarianceAnalysis
│       ├── Chart (variance_distribution)
│       ├── Table<VarianceItem>
│       │   ├── item
│       │   ├── variance_pct
│       │   └── recommendation
│       └── AiInsight × N
└── AiDock
    ├── AgentCard (Pricing Agent)
    └── EvidencePanel (cost insights)
```

## Data Sources

### Cost Comparison
```typescript
// API: GET /api/v1/pricing/compare/{tender_id}
interface CostComparison {
  tender_id: string;
  our_bid: CostBreakdown;
  sor_rates: CostBreakdown;
  market_rates: CostBreakdown;
  variance_analysis: VarianceAnalysis;
}

interface CostBreakdown {
  total: number;
  items: CostItem[];
}

interface CostItem {
  item_code: string;
  description: string;
  rate: number;
  quantity: number;
  total: number;
}

interface VarianceAnalysis {
  total_variance: number;
  variance_pct: number;
  items: VarianceItem[];
}

interface VarianceItem {
  item_code: string;
  description: string;
  our_rate: number;
  comparison_rate: number;
  variance: number;
  variance_pct: number;
  recommendation: string;
}
```

### React Query
```typescript
const { data: comparison } = useQuery({
  queryKey: ['pricing', 'compare', tenderId],
  queryFn: () => api.get(`/api/v1/pricing/compare/${tenderId}`),
});
```

## Zustand Store
```typescript
// stores/costComparisonStore.ts
interface CostComparisonState {
  selectedItems: Set<string>;
  showDetails: boolean;
  toggleItem: (code: string) => void;
  setShowDetails: (show: boolean) => void;
}
```

## Interactions

### View Comparison
1. Load comparison data
2. View side-by-side table
3. Analyze variances
4. Identify opportunities

### Analyze Variance
1. Click variance item
2. View detailed breakdown
3. Read recommendations
4. Adjust rates

### Export Comparison
1. Click Export button
2. Choose format
3. Include all details
4. Download report

### Optimize Costs
1. View AI recommendations
2. Apply optimizations
3. Update bid
4. Save changes

## Responsive Breakpoints

| Breakpoint | Layout |
|------------|--------|
| Desktop (>1024px) | Full comparison table |
| Tablet (768-1024px) | Horizontal scroll |
| Mobile (<768px) | Stacked cards |

## Loading States
- Comparison: Skeleton table
- Items: Skeleton rows
- Variance: Skeleton chart

## Error States
- Load failure: Retry button
- No data: EmptyState
- Network error: Toast notification

## Accessibility
- Table cells are focusable
- Variances highlighted via `aria-live`
- Screen reader: "Our bid: 50M, SOR: 48M, variance: 4%"
- Keyboard: Arrow keys to navigate

## Telemetry
- `cost_comparison.view` — Screen loaded
- `cost_comparison.item_click` — Item viewed
- `cost_comparison.export` — Comparison exported
- `cost_comparison.optimize` — Optimization applied

## Implementation Notes
- Side-by-side comparison table
- Variance analysis with charts
- AI-powered recommendations
- AiDock provides cost insights
- Export for decision documentation
