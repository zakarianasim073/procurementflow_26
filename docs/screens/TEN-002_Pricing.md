# TEN-002: Pricing Strategy Screen Specification

**Module:** `features/pricing/PricingPage`
**Layer:** features
**Version:** 1.0.0
**Status:** Draft
**Workspace:** Acquisition

## Purpose
AI-powered pricing strategy development with market intelligence, competitor analysis, margin optimization, and bid composition.

## Screen Layout

```
┌─────────────────────────────────────────────────────────────┐
│ ExecutiveHeader                                             │
├──────────┬──────────────────────────────────────────────────┤
│          │ Breadcrumb: Acquisition > Pricing > {Tender}     │
│ Workspace├──────────────────────────────────────────────────┤
│   Nav    │ PricingHeader (tender info, key metrics)         │
│          ├──────────────────────────────────────────────────┤
│          │ Tabs: [Market] [Competitors] [Composition] [Risk]│
│          ├──────────────────────────────────────────────────┤
│          │ Tab Content Area                                 │
│          │ ┌────────────────────────────────────────────┐   │
│          │ │ Market: MarketPrices, PriceHistory, Trends │   │
│          │ │ Competitors: CompetitorBids, WinPatterns   │   │
│          │ │ Composition: CostBreakdown, Margins        │   │
│          │ │ Risk: RiskMatrix, SensitivityAnalysis      │   │
│          │ └────────────────────────────────────────────┘   │
├──────────┴──────────────────────────────────────────────────┤
│ AiDock (pricing recommendations, optimization)              │
└─────────────────────────────────────────────────────────────┘
```

## Component Tree

```
PricingPage
├── ExecutiveHeader
├── Breadcrumb
├── PricingHeader
│   ├── TenderCard (compact)
│   └── KpiStrip (estimated_value, suggested_bid, margin, confidence)
├── Tabs
│   ├── MarketTab
│   │   ├── MarketPrices (table)
│   │   ├── PriceHistory (line chart)
│   │   └── TrendAnalysis (sparklines)
│   ├── CompetitorsTab
│   │   ├── CompetitorBids (table)
│   │   ├── WinPatterns (chart)
│   │   └── BidRatioAnalysis (gauge)
│   ├── CompositionTab
│   │   ├── CostBreakdown (tree/table)
│   │   ├── MarginAnalysis (gauge)
│   │   └── BidComposition (form)
│   └── RiskTab
│       ├── RiskMatrix (heatmap)
│       ├── SensitivityAnalysis (chart)
│       └── RiskMitigation (checklist)
└── AiDock
    ├── AgentCard (Pricing Agent)
    └── EvidencePanel (recommendations)
```

## Data Sources

### Market Intelligence
```typescript
// API: GET /api/v1/pricing/market/{tender_id}
interface MarketPrices {
  tender_id: string;
  items: MarketPriceItem[];
  market_trend: 'rising' | 'stable' | 'falling';
  confidence: number;
}

interface MarketPriceItem {
  item_code: string;
  description: string;
  current_price: number;
  historical_avg: number;
  trend: 'rising' | 'stable' | 'falling';
  source: string;
  confidence: number;
}
```

### Competitor Analysis
```typescript
// API: GET /api/v1/pricing/competitors/{tender_id}
interface CompetitorBids {
  tender_id: string;
  competitors: CompetitorBid[];
  avg_bid_ratio: number;
  win_pattern: string;
}

interface CompetitorBid {
  competitor_id: string;
  name: string;
  estimated_bid: number;
  bid_ratio: number;
  win_history: number;
  specializations: string[];
}
```

### Bid Composition
```typescript
// API: POST /api/v1/pricing/estimate
interface BidComposition {
  tender_id: string;
  items: BidItem[];
  total_cost: number;
  margin_pct: number;
  suggested_bid: number;
  confidence: number;
}

interface BidItem {
  item_code: string;
  quantity: number;
  unit_cost: number;
  margin_pct: number;
  bid_price: number;
  notes: string;
}
```

### React Query
```typescript
const { data: market } = useQuery({
  queryKey: ['pricing', tenderId, 'market'],
  queryFn: () => api.get(`/api/v1/pricing/market/${tenderId}`),
});

const { data: competitors } = useQuery({
  queryKey: ['pricing', tenderId, 'competitors'],
  queryFn: () => api.get(`/api/v1/pricing/competitors/${tenderId}`),
});

const { data: composition } = useQuery({
  queryKey: ['pricing', tenderId, 'composition'],
  queryFn: () => api.get(`/api/v1/pricing/estimate/${tenderId}`),
});

const optimizeBid = useMutation({
  mutationFn: (params: OptimizeParams) =>
    api.post(`/api/v1/pricing/optimize/${tenderId}`, params),
});
```

## Zustand Store
```typescript
// stores/pricingStore.ts
interface PricingState {
  activeTab: 'market' | 'competitors' | 'composition' | 'risk';
  marginTarget: number;
  riskLevel: 'conservative' | 'moderate' | 'aggressive';
  setActiveTab: (tab: string) => void;
  setMarginTarget: (margin: number) => void;
  setRiskLevel: (level: string) => void;
}
```

## Interactions

### Tab Switching
1. Click tab header
2. Update URL: `/pricing/{tender_id}?tab=market`
3. Preserve scroll position per tab
4. Lazy load tab content

### Market Analysis
1. View item prices with trends
2. Click item for historical chart
3. Filter by item category
4. Export market report

### Competitor Intelligence
1. View competitor bid estimates
2. Click competitor for profile
3. Analyze win patterns
4. Adjust strategy based on insights

### Bid Composition
1. Edit item costs/margins
2. Real-time total calculation
3. Optimize button → AI recommendation
4. Save draft bid

## Responsive Breakpoints

| Breakpoint | Layout |
|------------|--------|
| Desktop (>1024px) | Full tabs with content |
| Tablet (768-1024px) | Scrollable tabs |
| Mobile (<768px) | Bottom tab bar, stacked content |

## Loading States
- Tabs: Skeleton tab headers
- Content: Skeleton tables/charts
- KPIs: Skeleton cards

## Error States
- No market data: Manual entry
- Competitor data unavailable: Show estimated
- Optimization failure: Fallback to manual

## Accessibility
- Tab navigation with arrow keys
- Tab content announced on switch
- Screen reader: "Tab X of Y, {tab name}"
- Keyboard: Enter to activate tab

## Telemetry
- `pricing.view` — Screen loaded
- `pricing.tab_switch` — Tab changed
- `pricing.optimize` — Optimization requested
- `pricing.save_bid` — Bid saved

## Implementation Notes
- 4 tabs with lazy loading
- AiDock provides pricing intelligence
- Real-time bid calculation
- Optimization via AI agent
- Export to Excel/PDF
