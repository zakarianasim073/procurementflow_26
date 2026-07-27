# TEN-028: Pricing Comparison Screen Specification

**Module:** `features/pricing-comparison/PricingComparisonPage`
**Layer:** features
**Version:** 1.0.0
**Status:** Draft
**Workspace:** Acquisition

## Purpose
Compare pricing across multiple sources, agencies, and time periods.

## Screen Layout

```
┌─────────────────────────────────────────────────────────────┐
│ ExecutiveHeader                                             │
├──────────┬──────────────────────────────────────────────────┤
│          │ Breadcrumb: Acquisition > Pricing Comparison      │
│ Workspace├──────────────────────────────────────────────────┤
│   Nav    │ PricingComparisonHeader (sources, comparison)    │
│          ├──────────────────────────────────────────────────┤
│          │ PricingComparison (main content)                 │
│          │ ┌────────────────────────────────────────────┐   │
│          │ │ ComparisonTable (side-by-side)              │   │
│          │ │ ┌──────────┬──────────┬──────────┐          │   │
│          │ │ │ BWDB     │ PWD      │ LGED     │          │   │
│          │ │ │ Zone A   │ Zone A   │ Zone A   │          │   │
│          │ │ │ 100      │ 110      │ 95       │          │   │
│          │ │ └──────────┴──────────┴──────────┘          │   │
│          │ ├────────────────────────────────────────────┤   │
│          │ │ VarianceAnalysis (differences)              │   │
│          │ └────────────────────────────────────────────┘   │
├──────────┴──────────────────────────────────────────────────┤
│ AiDock (pricing insights)                                   │
└─────────────────────────────────────────────────────────────┘
```

## Component Tree

```
PricingComparisonPage
├── ExecutiveHeader
├── Breadcrumb
├── PricingComparisonHeader
│   ├── ChipSelect (agencies)
│   ├── ChipSelect (zones)
│   └── Button (Export Comparison)
├── PricingComparison
│   ├── ComparisonTable
│   │   └── Table<ComparisonRow>
│   │       ├── code
│   │       ├── description
│   │       ├── bwdb_rate
│   │       ├── pwd_rate
│   │       ├── lged_rate
│   │       └── variance
│   ├── VarianceAnalysis
│   │   ├── Chart (variance_distribution)
│   │   ├── Table<VarianceItem>
│   │   │   ├── agency
│   │   │   ├── avg_variance
│   │   │   └── count
│   │   └── AiInsight × N
│   ├── PriceHistory
│   │   └── Chart (price_trends)
│   └── SavingsReport
│       ├── total_savings
│       ├── recommended_source
│       └── items_count
└── AiDock
    ├── AgentCard (Pricing Agent)
    └── EvidencePanel (pricing insights)
```

## Data Sources

### Pricing Comparison
```typescript
// API: GET /api/v1/sor/pricing/compare
interface PricingComparison {
  items: ComparisonItem[];
  variances: VarianceItem[];
  savings: SavingsReport;
}

interface ComparisonItem {
  code: string;
  description: string;
  unit: string;
  rates: Record<string, number>; // agency_zone -> rate
  variance: number;
  best_source: string;
}

interface VarianceItem {
  agency: string;
  avg_variance: number;
  count: number;
  trend: 'increasing' | 'decreasing' | 'stable';
}

interface SavingsReport {
  total_savings: number;
  recommended_source: string;
  items_count: number;
  breakdown: { category: string; savings: number }[];
}
```

### React Query
```typescript
const { data: comparison } = useQuery({
  queryKey: ['sor', 'pricing', 'compare', filters],
  queryFn: () => api.get('/api/v1/sor/pricing/compare', { params: filters }),
});
```

## Zustand Store
```typescript
// stores/pricingComparisonStore.ts
interface PricingComparisonState {
  selectedAgencies: string[];
  selectedZones: string[];
  setAgencies: (agencies: string[]) => void;
  setZones: (zones: string[]) => void;
}
```

## Interactions

### Compare Rates
1. Select agencies
2. Select zones
3. View comparison
4. Analyze variances

### View Variance
1. Click variance cell
2. View details
3. Check history
4. Read insights

### View Savings
1. View savings report
2. Check recommendations
3. Review breakdown
4. Take action

### Export Comparison
1. Click Export
2. Choose format
3. Include all data
4. Download file

## Responsive Breakpoints

| Breakpoint | Layout |
|------------|--------|
| Desktop (>1024px) | Full comparison table |
| Tablet (768-1024px) | Horizontal scroll |
| Mobile (<768px) | Stacked cards |

## Loading States
- Table: Loading rows
- Variance: Loading chart
- Savings: Loading report

## Error States
- Load failure: Retry button
- Export failure: Toast error
- Network error: Toast notification

## Accessibility
- Table cells are focusable
- Variances highlighted via `aria-live`
- Screen reader: "BWDB: 100, PWD: 110, variance: 10%"
- Keyboard: Arrow keys to navigate

## Telemetry
- `pricing_comparison.view` — Screen loaded
- `pricing_comparison.compare` — Comparison performed
- `pricing_comparison.export` — Comparison exported

## Implementation Notes
- Side-by-side comparison
- Variance analysis
- Savings recommendations
- AiDock provides pricing insights
- Export for analysis
