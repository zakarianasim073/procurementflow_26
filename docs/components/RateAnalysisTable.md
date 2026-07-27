# RateAnalysisTable Component Contract

**Package**: `entities/pricing`  
**Type**: Data Display Component  
**Stability**: Stable  

---

## Purpose

Displays element-wise rate analysis with market cost breakdown, profit margins, and SOR vs market comparisons. Used in pricing workspace and executive reports.

---

## Props

```typescript
interface RateAnalysisTableProps {
  /** Rate analysis items */
  items: RateAnalysisItem[];
  /** Table configuration */
  config?: {
    /** Show market cost column */
    showMarketCost?: boolean;
    /** Show profit margin column */
    showProfitMargin?: boolean;
    /** Show SOR vs market column */
    showSorVsMarket?: boolean;
    /** Show element breakdown */
    showElements?: boolean;
    /** Expandable rows for elements */
    expandable?: boolean;
    /** Page size */
    pageSize?: number;
  };
  /** Row expand handler */
  onRowExpand?: (itemId: string, expanded: boolean) => void;
  /** Element click handler */
  onElementClick?: (element: RateElement) => void;
  /** Loading state */
  loading?: boolean;
  /** Error state */
  error?: string;
  /** Custom className */
  className?: string;
}

interface RateAnalysisItem {
  id: string;
  sorCode: string;
  description: string;
  quotedRate: number | null;
  sorRate: number | null;
  marketCostPerUnit: number | null;
  profitMarginPct: number | null;
  sorVsMarketPct: number | null;
  bidVsSorPct: number | null;
  hasComposition: boolean;
  elements: RateElement[];
  coveragePct: number;
  workType: string;
}

interface RateElement {
  subCode: string;
  subDesc: string;
  component: 'material' | 'labor' | 'equipment' | 'overhead';
  templateQty: number;
  templateUnit: string;
  marketCostPerWorkUnit: number | null;
  marketSource: 'sor' | 'market_index' | 'manual' | 'estimated';
}
```

---

## Slots

| Slot | Required | Description |
|------|----------|-------------|
| `header` | No | Title, legend, export actions |
| `footer` | No | Profit margin summary |
| `empty` | No | No composition data message |
| `elementRow` | No | Custom element rendering |

---

## State

| State | Trigger | Visual |
|-------|---------|--------|
| `loading` | `loading=true` | Row skeletons with expandable placeholders |
| `empty` | `items.length === 0` | "No rate analysis data" |
| `error` | `error` prop | Alert with retry |
| `expanded` | `expandable` + click | Element breakdown visible |
| `profitable` | `profitMarginPct > 15` | Green margin badge |
| `atRisk` | `0 < profitMarginPct ≤ 15` | Yellow margin badge |
| `loss` | `profitMarginPct ≤ 0` | Red margin badge |

---

## Accessibility

- **Role**: `table` with expandable rows (`aria-expanded`)
- **Headers**: `scope="col"` + profit margin `aria-label`
- **Expandable**: Button with `aria-controls` pointing to element row
- **Color**: Profit badges use icons + text (not color-only)
- **Keyboard**: Arrow keys navigate, Enter/Space toggles expansion

---

## Loading

- **Skeleton**: 5 rows with expandable skeleton rows
- **Delay**: 300ms (rate analysis involves market lookups)

---

## Errors

- **No Composition**: "Item [code] has no rate composition"
- **Market Data Missing**: "Market price unavailable for [component]"

---

## Keyboard

| Key | Action |
|-----|--------|
| `Tab` | Navigate cells |
| `Enter` / `Space` | Toggle row expansion |
| `Arrow Keys` | Navigate grid |
| `Escape` | Collapse all |

---

## Mobile

- **< 1024px**: Sticky `sorCode` + `description`, horizontal scroll
- **Expansion**: Full-width modal drawer for elements
- **Columns Hidden**: `coveragePct`, `bidVsSorPct` (toggle)

---

## Permissions

| Role | View | Export |
|------|------|--------|
| `viewer` | ✅ | ❌ |
| `estimator` | ✅ | ✅ |
| `compliance` | ✅ | ✅ |
| `admin` | ✅ | ✅ |

---

## Telemetry

| Event | Properties |
|-------|------------|
| `rate_analysis_view` | `item_count`, `items_with_composition` |
| `rate_analysis_expand` | `sor_code`, `element_count` |
| `rate_analysis_margin_check` | `sor_code`, `margin_pct`, `status` |

---

## React Query

```typescript
const { data } = useQuery({
  queryKey: pricingKeys.rateAnalysis(tenderId),
  select: (result) => result.rate_analysis.details
});
```

---

## Dependencies

- `DataTable` (base)
- `ProfitMarginBadge` (color-coded)
- `ElementBreakdown` (expandable row content)
- `CoverageIndicator` (progress ring)
- `ExportDropdown` (6-tab Excel export)

---

## Profit Margin Thresholds

| Status | Range | Badge Color | Icon |
|--------|-------|-------------|------|
| Safe | > 15% | `success` | `ShieldCheck` |
| Tight | 5–15% | `warning` | `AlertTriangle` |
| At Risk | 0–5% | `danger` | `XCircle` |
| Loss | ≤ 0% | `danger` | `AlertOctagon` |
| N/A | `null` | `muted` | `HelpCircle` |

---

## Future Extensions

- [ ] Scenario modeling (what-if analysis)
- [ ] Sensitivity tornado chart
- [ ] Monte Carlo simulation integration
- [ ] Benchmark comparison overlay