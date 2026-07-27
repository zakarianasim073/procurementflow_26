# BoqTable Component Contract

**Package**: `entities/boq`  
**Type**: Data Display Component  
**Stability**: Stable  

---

## Purpose

Displays BOQ comparison results in a sortable, filterable, paginated table with inline editing for quoted rates. Core component for tender pricing analysis.

---

## Props

```typescript
interface BoqTableProps {
  /** BOQ comparison data */
  data: BoqComparisonItem[];
  /** Table configuration */
  config?: {
    /** Show quoted rate column (editable) */
    showQuotedRate?: boolean;
    /** Show SOR rate column */
    showSorRate?: boolean;
    /** Show variance columns */
    showVariance?: boolean;
    /** Show flag column */
    showFlag?: boolean;
    /** Show section column */
    showSection?: boolean;
    /** Enable row selection */
    selectable?: boolean;
    /** Enable sorting */
    sortable?: boolean;
    /** Enable filtering */
    filterable?: boolean;
    /** Page size */
    pageSize?: number;
  };
  /** Row click handler */
  onRowClick?: (item: BoqComparisonItem) => void;
  /** Quoted rate change handler */
  onQuotedRateChange?: (itemId: string, newRate: number) => void;
  /** Selection change handler */
  onSelectionChange?: (selectedIds: string[]) => void;
  /** Loading state */
  loading?: boolean;
  /** Error state */
  error?: string;
  /** Custom className */
  className?: string;
}

interface BoqComparisonItem {
  id: string;
  itemNo: string;
  code: string;
  agency: string;
  workType: string;
  description: string;
  unit: string;
  quantity: number;
  quotedRate: number | null;
  sorRate: number | null;
  sorCode: string | null;
  diff: number | null;
  pctDiff: number | null;
  flag: 'MATCH' | 'BELOW_SOR' | 'ABOVE_SOR' | 'NO_RATE' | 'VARIANCE';
  section: string;
  matchType: 'exact' | 'prefix' | 'fuzzy' | 'manual' | 'none';
  confidence: number;
}
```

---

## Slots

| Slot | Required | Description |
|------|----------|-------------|
| `header` | No | Custom header (title, actions, export) |
| `footer` | No | Summary row (totals, averages) |
| `empty` | No | Empty state content |
| `rowActions` | No | Per-row action menu |

---

## State

| State | Trigger | Visual |
|-------|---------|--------|
| `loading` | `loading=true` | Row skeletons (5 rows) |
| `empty` | `data.length === 0` | Empty state illustration |
| `error` | `error` prop | Alert banner + retry |
| `sorting` | Column click | Sort indicator |
| `filtering` | Filter input | Filter chips |
| `editing` | Cell click (quoted rate) | Inline input |
| `selected` | Checkbox/click | Highlighted row |

---

## Accessibility

- **Role**: `table` with `caption` (hidden)
- **Headers**: `scope="col"` on all `<th>`
- **Sortable**: `aria-sort` on sortable headers
- **Row**: `role="row"` with `aria-selected` if selectable
- **Editable Cell**: `role="gridcell"` with `aria-label`
- **Keyboard**: Full grid navigation (arrows, Home, End)

---

## Loading

- **Skeleton**: 5 rows × 12 columns with shimmer
- **Delay**: 200ms (BOQ data can be slow)

---

## Errors

- **Empty**: "No BOQ items found for this comparison"
- **Parse Error**: "Failed to parse BOQ data — check file format"
- **Rate Error**: "SOR rate unavailable for item [code]"

---

## Keyboard

| Key | Action |
|-----|--------|
| `Tab` | Next cell |
| `Shift+Tab` | Previous cell |
| `Arrow Keys` | Navigate grid |
| `Enter` | Edit cell / activate row |
| `Escape` | Cancel edit / clear selection |
| `Space` | Toggle row selection |
| `Ctrl+A` | Select all |
| `Home` / `End` | First/last cell in row |

---

## Mobile

- **< 1024px**: Horizontal scroll with sticky first 3 columns
- **Columns Hidden**: `section`, `matchType`, `confidence` (toggle via "Columns" button)
- **Row Height**: Increased to 56px for touch
- **Actions**: Collapsed into kebab menu

---

## Permissions

| Role | View | Edit Quoted Rate | Export |
|------|------|------------------|--------|
| `viewer` | ✅ | ❌ | ❌ |
| `estimator` | ✅ | ✅ | ✅ |
| `compliance` | ✅ | ❌ | ✅ |
| `admin` | ✅ | ✅ | ✅ |

---

## Telemetry

| Event | Properties |
|-------|------------|
| `boq_table_view` | `row_count`, `config` |
| `boq_table_sort` | `column`, `direction` |
| `boq_table_filter` | `column`, `value` |
| `boq_table_edit` | `item_id`, `field`, `old_value`, `new_value` |
| `boq_table_export` | `format`, `row_count` |

---

## React Query

```typescript
const { data } = useQuery({
  queryKey: boqKeys.jobResult(jobId),
  select: (result) => ({
    data: result.data.map(item => ({
      ...item,
      flag: item.flag || 'NO_RATE',
      confidence: item.confidence ?? 0
    }))
  })
});
```

---

## Dependencies

- `DataTable` (base table component)
- `FlagBadge` (for flag column)
- `CurrencyInput` (for quoted rate editing)
- `CurrencyDisplay` / `PercentageDisplay` (formatters)
- `MatchTypeBadge` (for match type)
- `ColumnSelector` (mobile column toggle)
- `ExportDropdown` (Excel/DOCX/PDF)

---

## Column Definitions

| Column | Key | Width | Sortable | Filterable | Editable |
|--------|-----|-------|----------|------------|----------|
| Item No | `itemNo` | 80px | ✅ | ✅ | ❌ |
| Code | `code` | 120px | ✅ | ✅ | ❌ |
| Agency | `agency` | 80px | ✅ | ✅ | ❌ |
| Work Type | `workType` | 140px | ✅ | ✅ | ❌ |
| Description | `description` | 300px | ✅ | ✅ | ❌ |
| Unit | `unit` | 80px | ✅ | ❌ | ❌ |
| Qty | `quantity` | 100px | ✅ | ❌ | ❌ |
| Quoted Rate | `quotedRate` | 120px | ✅ | ❌ | ✅ |
| SOR Rate | `sorRate` | 120px | ✅ | ❌ | ❌ |
| Diff | `diff` | 100px | ✅ | ❌ | ❌ |
| % Diff | `pctDiff` | 100px | ✅ | ❌ | ❌ |
| Flag | `flag` | 100px | ✅ | ✅ | ❌ |

---

## Future Extensions

- [ ] Inline formula editor for quoted rate
- [ ] Bulk edit mode (multi-row)
- [ ] Version history per cell
- [ ] AI-suggested rate with confidence
- [ ] Drag-to-reorder items