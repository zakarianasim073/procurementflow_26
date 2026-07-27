# TEN-009: Bid Comparison Screen Specification

**Module:** `features/bid-comparison/BidComparisonPage`
**Layer:** features
**Version:** 1.0.0
**Status:** Draft
**Workspace:** Acquisition

## Purpose
Side-by-side bid comparison, competitor analysis, and bid optimization for tender decision making.

## Screen Layout

```
┌─────────────────────────────────────────────────────────────┐
│ ExecutiveHeader                                             │
├──────────┬──────────────────────────────────────────────────┤
│          │ Breadcrumb: Acquisition > Bid Comparison          │
│ Workspace├──────────────────────────────────────────────────┤
│   Nav    │ BidComparisonHeader (tender context)             │
│          ├──────────────────────────────────────────────────┤
│          │ BidComparison (main content)                     │
│          │ ┌────────────────────────────────────────────┐   │
│          │ │ ComparisonTable (side-by-side)              │   │
│          │ │ ┌──────────┬──────────┬──────────┐          │   │
│          │ │ │ Our Bid  │ Comp A   │ Comp B   │          │   │
│          │ │ │ 50M      │ 45M      │ 55M      │          │   │
│          │ │ ├──────────┼──────────┼──────────┤          │   │
│          │ │ │ Items    │ Items    │ Items    │          │   │
│          │ │ │ Rates    │ Rates    │ Rates    │          │   │
│          │ │ │ Margin   │ Margin   │ Margin   │          │   │
│          │ │ └──────────┴──────────┴──────────┘          │   │
│          │ ├────────────────────────────────────────────┤   │
│          │ │ OptimizationPanel (AI suggestions)          │   │
│          │ └────────────────────────────────────────────┘   │
├──────────┴──────────────────────────────────────────────────┤
│ AiDock (bid optimization, strategy recommendations)         │
└─────────────────────────────────────────────────────────────┘
```

## Component Tree

```
BidComparisonPage
├── ExecutiveHeader
├── Breadcrumb
├── BidComparisonHeader
│   ├── TenderCard (compact)
│   └── KpiStrip (our_bid, competitor_avg, win_probability)
├── BidComparison
│   ├── ComparisonTable
│   │   └── Table<BidComparison>
│   │       ├── category
│   │       ├── our_bid
│   │       ├── competitor_a
│   │       ├── competitor_b
│   │       └── difference
│   ├── ItemBreakdown
│   │   └── Table<ItemComparison>
│   │       ├── item_code
│   │       ├── our_rate
│   │       ├── competitor_rate
│   │       └── variance
│   └── OptimizationPanel
│       ├── Recommendation × N
│       │   ├── type
│       │   ├── description
│       │   ├── impact
│       │   └── Button (Apply)
│       └── ConfidenceBadge
└── AiDock
    ├── AgentCard (Pricing Agent)
    └── EvidencePanel (optimization insights)
```

## Data Sources

### Bid Comparison
```typescript
// API: GET /api/v1/pricing/compare/{tender_id}
interface BidComparison {
  tender_id: string;
  our_bid: BidDetails;
  competitors: CompetitorBid[];
  analysis: ComparisonAnalysis;
}

interface BidDetails {
  total: number;
  items: ItemBid[];
  margin_pct: number;
  win_probability: number;
}

interface CompetitorBid {
  competitor_id: string;
  name: string;
  total: number;
  items: ItemBid[];
  margin_pct: number;
  estimated: boolean;
}

interface ItemBid {
  item_code: string;
  rate: number;
  quantity: number;
  total: number;
}

interface ComparisonAnalysis {
  price_position: 'lowest' | 'middle' | 'highest';
  competitive_advantage: string[];
  risks: string[];
  recommendations: Recommendation[];
}

interface Recommendation {
  type: 'price' | 'item' | 'strategy';
  description: string;
  impact: number;
  confidence: number;
}
```

### React Query
```typescript
const { data: comparison } = useQuery({
  queryKey: ['pricing', 'compare', tenderId],
  queryFn: () => api.get(`/api/v1/pricing/compare/${tenderId}`),
});

const applyRecommendation = useMutation({
  mutationFn: (request: ApplyRecommendationRequest) =>
    api.post(`/api/v1/pricing/compare/${tenderId}/apply`, request),
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ['pricing', 'compare', tenderId] });
    toast.success('Recommendation applied');
  },
});
```

## Zustand Store
```typescript
// stores/bidComparisonStore.ts
interface BidComparisonState {
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
3. Analyze differences
4. Identify opportunities

### Apply Recommendation
1. Click recommendation
2. View details
3. Confirm application
4. Update bid

### Item Analysis
1. Click item row
2. View detailed comparison
3. Analyze variance
4. Adjust rates

### Export Comparison
1. Click Export button
2. Choose format
3. Include all details
4. Download report

## Responsive Breakpoints

| Breakpoint | Layout |
|------------|--------|
| Desktop (>1024px) | Full comparison table |
| Tablet (768-1024px) | Horizontal scroll |
| Mobile (<768px) | Stacked cards |

## Loading States
- Comparison: Skeleton table
- Items: Skeleton rows
- Recommendations: Skeleton cards

## Error States
- No competitors: Estimated values
- Data unavailable: Manual entry
- Network error: Retry button

## Accessibility
- Table cells are focusable
- Differences highlighted via `aria-live`
- Screen reader: "Our bid: 50M, Competitor: 45M"
- Keyboard: Arrow keys to navigate

## Telemetry
- `bid_comparison.view` — Screen loaded
- `bid_comparison.apply` — Recommendation applied
- `bid_comparison.export` — Comparison exported

## Implementation Notes
- Side-by-side comparison table
- Item-level variance analysis
- AI-powered optimization
- AiDock provides strategy insights
- Export for decision documentation
