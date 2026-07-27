# TEN-029: Bid Analysis Screen Specification

**Module:** `features/bid-analysis/BidAnalysisPage`
**Layer:** features
**Version:** 1.0.0
**Status:** Draft
**Workspace:** Acquisition

## Purpose
Analyze bids, compare proposals, and evaluate competitiveness.

## Screen Layout

```
┌─────────────────────────────────────────────────────────────┐
│ ExecutiveHeader                                             │
├──────────┬──────────────────────────────────────────────────┤
│          │ Breadcrumb: Acquisition > Bid Analysis            │
│ Workspace├──────────────────────────────────────────────────┤
│   Nav    │ BidAnalysisHeader (tender, bid_count)            │
│          ├──────────────────────────────────────────────────┤
│          │ BidAnalysis (main content)                       │
│          │ ┌────────────────────────────────────────────┐   │
│          │ │ KpiStrip (key metrics)                     │   │
│          │ ├────────────────────────────────────────────┤   │
│          │ │ Tabs: [Overview] [Comparison] [Scoring]    │   │
│          │ ├────────────────────────────────────────────┤   │
│          │ │ OverviewTab (summary charts)                │   │
│          │ │ ComparisonTab (bid comparison)              │   │
│          │ │ ScoringTab (evaluation scores)              │   │
│          │ └────────────────────────────────────────────┘   │
├──────────┴──────────────────────────────────────────────────┤
│ AiDock (bid insights)                                       │
└─────────────────────────────────────────────────────────────┘
```

## Component Tree

```
BidAnalysisPage
├── ExecutiveHeader
├── Breadcrumb
├── BidAnalysisHeader
│   ├── KpiStrip (bid_count, avg_price, recommended_bid)
│   └── Button (Export Analysis)
├── BidAnalysis
│   ├── Tabs
│   │   ├── OverviewTab
│   │   │   ├── Chart (price_distribution)
│   │   │   ├── Chart (bidder_comparison)
│   │   │   └── Chart (score_breakdown)
│   │   ├── ComparisonTab
│   │   │   └── ComparisonTable
│   │   │       └── TableRow × N
│   │   │           ├── bidder
│   │   │           ├── price
│   │   │           ├── technical_score
│   │   │           ├── financial_score
│   │   │           └── total_score
│   │   └── ScoringTab
│   │       └── ScoringMatrix
│   │           └── Criteria × N
│   │               ├── name
│   │               ├── weight
│   │               └── scores
│   ├── BidDetails
│   │   ├── bid_info
│   │   ├── proposal_summary
│   │   └── strengths_weaknesses
│   └── RecommendationReport
│       ├── recommended_bidder
│       ├── justification
│       └── risk_assessment
└── AiDock
    ├── AgentCard (Analysis Agent)
    └── EvidencePanel (bid insights)
```

## Data Sources

### Bid Analysis
```typescript
// API: GET /api/v1/tenders/{tender_id}/bids/analysis
interface BidAnalysis {
  tender_id: string;
  bids: Bid[];
  comparison: ComparisonData;
  scoring: ScoringMatrix;
  recommendation: Recommendation;
}

interface Bid {
  bid_id: string;
  bidder_name: string;
  price: number;
  technical_score: number;
  financial_score: number;
  total_score: number;
  strengths: string[];
  weaknesses: string[];
}

interface ComparisonData {
  price_range: { min: number; max: number; avg: number };
  score_distribution: { bidder: string; score: number }[];
}

interface ScoringMatrix {
  criteria: Criteria[];
  weights: Record<string, number>;
}

interface Criteria {
  name: string;
  description: string;
  max_score: number;
  scores: Record<string, number>;
}

interface Recommendation {
  recommended_bidder: string;
  justification: string;
  risk_level: 'low' | 'medium' | 'high';
  risks: string[];
}
```

### React Query
```typescript
const { data: analysis } = useQuery({
  queryKey: ['tenders', tenderId, 'bids', 'analysis'],
  queryFn: () => api.get(`/api/v1/tenders/${tenderId}/bids/analysis`),
  enabled: !!tenderId,
});
```

## Zustand Store
```typescript
// stores/bidAnalysisStore.ts
interface BidAnalysisState {
  activeTab: string;
  setTab: (tab: string) => void;
}
```

## Interactions

### View Overview
1. Click Overview tab
2. View charts
3. Analyze distribution
4. Check scores

### Compare Bids
1. Click Comparison tab
2. View table
3. Compare prices
4. Check scores

### View Scoring
1. Click Scoring tab
2. View matrix
3. Check criteria
4. Review weights

### View Recommendation
1. View report
2. Read justification
3. Check risks
4. Make decision

## Responsive Breakpoints

| Breakpoint | Layout |
|------------|--------|
| Desktop (>1024px) | Full tabs + charts |
| Tablet (768-1024px) | Stacked tabs |
| Mobile (<768px) | Simplified view |

## Loading States
- Analysis: Loading charts
- Comparison: Loading table
- Scoring: Loading matrix

## Error States
- Load failure: Retry button
- Export failure: Toast error
- Network error: Toast notification

## Accessibility
- Charts are keyboard navigable
- Metrics announced via `aria-live`
- Screen reader: "Recommended bidder: ABC Corp"
- Keyboard: Tab through charts

## Telemetry
- `bid_analysis.view` — Screen loaded
- `bid_analysis.tab_change` — Tab changed
- `bid_analysis.export` — Analysis exported

## Implementation Notes
- Comprehensive bid analysis
- Comparison tables
- Scoring matrices
- AiDock provides bid insights
- Export for decision making
