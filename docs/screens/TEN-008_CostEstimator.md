# TEN-008: Cost Estimator Screen Specification

**Module:** `features/cost-estimator/CostEstimatorPage`
**Layer:** features
**Version:** 1.0.0
**Status:** Draft
**Workspace:** Acquisition

## Purpose
Detailed cost estimation with material, labor, equipment breakdowns, margin analysis, and bid composition.

## Screen Layout

```
┌─────────────────────────────────────────────────────────────┐
│ ExecutiveHeader                                             │
├──────────┬──────────────────────────────────────────────────┤
│          │ Breadcrumb: Acquisition > Cost Estimator          │
│ Workspace├──────────────────────────────────────────────────┤
│   Nav    │ CostEstimatorHeader (tender info, total)         │
│          ├──────────────────────────────────────────────────┤
│          │ CostEstimator (main content)                     │
│          │ ┌────────────────────────────────────────────┐   │
│          │ │ Tabs: [Materials] [Labor] [Equipment]      │   │
│          │ │ [Overhead] [Margin] [Summary]               │   │
│          │ ├────────────────────────────────────────────┤   │
│          │ │ CostBreakdownTable (editable)              │   │
│          │ │ SubtotalBar (category totals)              │   │
│          │ │ MarginAnalysis (gauge + sliders)           │   │
│          │ │ FinalSummary (total bid)                   │   │
│          │ └────────────────────────────────────────────┘   │
├──────────┴──────────────────────────────────────────────────┤
│ AiDock (cost optimization, margin suggestions)              │
└─────────────────────────────────────────────────────────────┘
```

## Component Tree

```
CostEstimatorPage
├── ExecutiveHeader
├── Breadcrumb
├── CostEstimatorHeader
│   ├── TenderCard (compact)
│   └── KpiStrip (total_cost, margin, final_bid)
├── CostEstimator
│   ├── Tabs
│   │   ├── MaterialsTab
│   │   │   └── CostBreakdownTable
│   │   │       └── CostRow × N
│   │   │           ├── item_code
│   │   │           ├── description
│   │   │           ├── quantity
│   │   │           ├── unit_cost
│   │   │           └── total
│   │   ├── LaborTab
│   │   │   └── CostBreakdownTable
│   │   ├── EquipmentTab
│   │   │   └── CostBreakdownTable
│   │   ├── OverheadTab
│   │   │   └── OverheadForm
│   │   │       ├── Input (admin_cost)
│   │   │       ├── Input (contingency)
│   │   │       └── Input (profit)
│   │   ├── MarginTab
│   │   │   └── MarginAnalysis
│   │   │       ├── Gauge (margin_pct)
│   │   │       ├── RangeSlider (adjust margin)
│   │   │       └── Chart (sensitivity)
│   │   └── SummaryTab
│   │       └── FinalSummary
│   │           ├── KpiCard (materials_total)
│   │           ├── KpiCard (labor_total)
│   │           ├── KpiCard (equipment_total)
│   │           ├── KpiCard (overhead_total)
│   │           ├── KpiCard (margin_amount)
│   │           └── KpiCard (final_bid)
│   └── ActionButtons
│       ├── Button (Save Draft)
│       ├── Button (Export)
│       └── Button (Apply to Bid)
└── AiDock
    ├── AgentCard (Pricing Agent)
    └── EvidencePanel (cost insights)
```

## Data Sources

### Cost Data
```typescript
// API: GET /api/v1/pricing/estimate/{tender_id}
interface CostEstimate {
  tender_id: string;
  materials: CostItem[];
  labor: CostItem[];
  equipment: CostItem[];
  overhead: OverheadCost;
  margin_pct: number;
  total_cost: number;
  final_bid: number;
}

interface CostItem {
  item_code: string;
  description: string;
  quantity: number;
  unit: string;
  unit_cost: number;
  total: number;
  source: 'sor' | 'market' | 'manual';
  confidence: number;
}

interface OverheadCost {
  admin_cost: number;
  contingency: number;
  profit: number;
}
```

### Save Estimate
```typescript
// API: POST /api/v1/pricing/estimate/{tender_id}
interface SaveEstimateRequest {
  materials: CostItem[];
  labor: CostItem[];
  equipment: CostItem[];
  overhead: OverheadCost;
  margin_pct: number;
}
```

### React Query
```typescript
const { data: estimate } = useQuery({
  queryKey: ['pricing', 'estimate', tenderId],
  queryFn: () => api.get(`/api/v1/pricing/estimate/${tenderId}`),
});

const saveEstimate = useMutation({
  mutationFn: (request: SaveEstimateRequest) =>
    api.post(`/api/v1/pricing/estimate/${tenderId}`, request),
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ['pricing', 'estimate', tenderId] });
    toast.success('Estimate saved');
  },
});
```

## Zustand Store
```typescript
// stores/costEstimatorStore.ts
interface CostEstimatorState {
  activeTab: string;
  hasUnsavedChanges: boolean;
  setTab: (tab: string) => void;
  setUnsavedChanges: (hasChanges: boolean) => void;
}
```

## Interactions

### Edit Cost Item
1. Click cost row
2. Edit quantity/unit_cost
3. Auto-calculate total
4. Mark as unsaved

### Adjust Margin
1. Move margin slider
2. Real-time final bid update
3. View sensitivity chart
4. Save when satisfied

### Apply to Bid
1. Click "Apply to Bid"
2. Confirm overwrite
3. Update bid composition
4. Redirect to submission

### Export Estimate
1. Click Export button
2. Choose format (Excel/PDF)
3. Include all breakdowns
4. Download file

## Responsive Breakpoints

| Breakpoint | Layout |
|------------|--------|
| Desktop (>1024px) | Full tabs with table |
| Tablet (768-1024px) | Stacked tabs |
| Mobile (<768px) | Single tab view |

## Loading States
- Table: Skeleton rows
- Margin: Skeleton gauge
- Summary: Skeleton cards

## Error States
- Save failure: Draft recovery
- Calculation error: Validation message
- Network error: Retry button

## Accessibility
- Editable cells are focusable
- Changes announced via `aria-live`
- Screen reader: "Total: 50,000 BDT"
- Keyboard: Enter to edit, Tab to next cell

## Telemetry
- `cost_estimator.view` — Screen loaded
- `cost_estimator.edit` — Cost item edited
- `cost_estimator.save` — Estimate saved
- `cost_estimator.apply` — Applied to bid

## Implementation Notes
- 6 tabs with editable tables
- Real-time calculation
- Margin sensitivity analysis
- AiDock provides cost insights
- Export for documentation
