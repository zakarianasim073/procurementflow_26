# TEN-001: BOQ Analysis Screen Specification

**Module:** `features/boq/BoqAnalysisPage`
**Layer:** features
**Version:** 1.0.0
**Status:** Draft
**Workspace:** Acquisition

## Purpose
Bill of Quantities analysis with SOR rate matching, cost estimation, variance detection, and AI-powered pricing recommendations.

## Screen Layout

```
┌─────────────────────────────────────────────────────────────┐
│ ExecutiveHeader                                             │
├──────────┬──────────────────────────────────────────────────┤
│          │ Breadcrumb: Acquisition > BOQ Analysis > {Tender}│
│ Workspace├──────────────────────────────────────────────────┤
│   Nav    │ TenderContext (tender card + metrics)             │
│          ├──────────────────────────────────────────────────┤
│          │ SplitPane (horizontal)                           │
│          │ ┌─────────────────────┬─────────────────────┐    │
│          │ │ BOQTable            │ RateAnalysisTable    │    │
│          │ │ (items, quantities, │ (SOR rates, variance,│    │
│          │ │  descriptions)      │  recommendations)    │    │
│          │ └─────────────────────┴─────────────────────┘    │
│          ├──────────────────────────────────────────────────┤
│          │ SummaryBar (total, variance, confidence)         │
├──────────┴──────────────────────────────────────────────────┤
│ AiDock (pricing recommendations, SOR suggestions)           │
└─────────────────────────────────────────────────────────────┘
```

## Component Tree

```
BoqAnalysisPage
├── ExecutiveHeader
├── Breadcrumb
├── TenderContext
│   ├── TenderCard (compact)
│   └── KpiStrip (estimated_value, item_count, match_rate)
├── SplitPane
│   ├── BoqTable
│   │   ├── TableHeader (columns)
│   │   └── VirtualList<BoqItem>
│   │       └── BoqRow × N
│   │           ├── item_code
│   │           ├── description
│   │           ├── unit
│   │           ├── quantity
│   │           └── ConfidenceBadge (match confidence)
│   └── RateAnalysisTable
│       ├── TableHeader (SOR rate, variance)
│       └── VirtualList<RateAnalysis>
│           └── RateRow × N
│               ├── sor_code
│               ├── sor_description
│               ├── sor_rate
│               ├── variance_pct
│               └── ConfidenceBadge
├── SummaryBar
│   ├── KpiCard (total_boq_value)
│   ├── KpiCard (total_sor_value)
│   ├── KpiCard (variance_pct)
│   └── KpiCard (match_confidence)
└── AiDock
    ├── AgentCard (Pricing Agent)
    └── EvidencePanel (SOR suggestions)
```

## Data Sources

### BOQ Items
```typescript
// API: GET /api/v1/boq/{tender_id}/items
interface BoqItem {
  item_code: string;
  description: string;
  unit: string;
  quantity: number;
  rate?: number;
  amount?: number;
  sor_matches: SorMatch[];
  confidence: number;
}

interface SorMatch {
  sor_code: string;
  agency: string;
  description: string;
  rate_a: number;
  rate_b: number;
  rate_c: number;
  rate_d: number;
  match_score: number;
  match_type: 'exact' | 'prefix' | 'fuzzy';
}
```

### Rate Analysis
```typescript
// API: GET /api/v1/boq/{tender_id}/analysis
interface RateAnalysis {
  item_code: string;
  boq_rate: number;
  sor_rate: number;
  variance: number;
  variance_pct: number;
  recommendation: 'use_sor' | 'use_boq' | 'negotiate';
  confidence: number;
  evidence: string;
}
```

### React Query
```typescript
const { data: boqItems } = useQuery({
  queryKey: ['boq', tenderId, 'items'],
  queryFn: () => api.get(`/api/v1/boq/${tenderId}/items`),
});

const { data: analysis } = useQuery({
  queryKey: ['boq', tenderId, 'analysis'],
  queryFn: () => api.get(`/api/v1/boq/${tenderId}/analysis`),
  enabled: !!boqItems,
});
```

## Zustand Store
```typescript
// stores/boqStore.ts
interface BoqState {
  selectedItem: string | null;
  filterMatchType: 'all' | 'exact' | 'prefix' | 'fuzzy';
  filterConfidence: number;
  sortBy: 'item_code' | 'variance' | 'confidence';
  setSelectedItem: (code: string | null) => void;
  setFilter: (key: string, value: any) => void;
  setSortBy: (sort: string) => void;
}
```

## Interactions

### Item Selection
1. Click BoqItem row
2. Highlight row in both tables
3. Show details in Drawer
4. AiDock shows related suggestions

### Rate Variance Click
1. Click variance percentage
2. Open EvidencePanel
3. Show SOR source documents
4. AI recommendation for resolution

### Bulk Operations
1. Select multiple items (Ctrl+Click)
2. Bulk actions: Export, Re-match, Report
3. Apply SOR rates to selected

### Export
1. Click Export button
2. Choose format: Excel, PDF, CSV
3. POST `/api/v1/boq/{tender_id}/export`
4. Download generated file

## Responsive Breakpoints

| Breakpoint | Layout |
|------------|--------|
| Desktop (>1024px) | Split pane side-by-side |
| Tablet (768-1024px) | Tabbed view (BOQ / Analysis) |
| Mobile (<768px) | Stacked cards per item |

## Loading States
- BOQTable: 20 skeleton rows
- RateAnalysis: 20 skeleton rows
- Summary: Skeleton KPI cards

## Error States
- Parse failure: Manual entry mode
- SOR mismatch: Warning + fallback
- Export failure: Toast error

## Accessibility
- Table navigation with arrow keys
- Row selection announced via `aria-live`
- Screen reader: "Item X of Y, variance Z%"
- Keyboard: Enter to expand details

## Telemetry
- `boq.view` — Screen loaded
- `boq.item_select` — Item selected
- `boq.variance_click` — Variance clicked
- `boq.export` — Export triggered

## Implementation Notes
- SplitPane resizable by user
- VirtualList for 500+ BOQ items
- Real-time SOR matching via API
- AiDock provides pricing intelligence
- TrustPanel shows match confidence
