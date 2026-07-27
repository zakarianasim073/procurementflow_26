# FilterPanel Component Contract

**Package**: `widgets/search`  
**Type**: Filter Component  
**Stability**: Stable  

---

## Purpose

Collapsible filter sidebar with multi-select, range sliders, date pickers, and active filter chips. Used in OPP-001 Discovery, TEN-001 BOQ, KNOW-001 Search screens.

---

## Props

```typescript
interface FilterPanelProps {
  /** Filter configuration */
  filters: FilterConfig[];
  /** Current filter values */
  values: Record<string, FilterValue>;
  /** Change handler */
  onChange: (values: Record<string, FilterValue>) => void;
  /** Clear all handler */
  onClear: () => void;
  /** Collapsed state */
  collapsed?: boolean;
  onCollapseChange?: (collapsed: boolean) => void;
  /** Show active count badge */
  showCount?: boolean;
  /** Custom className */
  className?: string;
}

interface FilterConfig {
  key: string;
  label: string;
  type: 'select' | 'multi-select' | 'range' | 'date-range' | 'boolean' | 'text';
  options?: FilterOption[];
  placeholder?: string;
  min?: number;
  max?: number;
  step?: number;
  unit?: string;
  searchable?: boolean;
  group?: string;
}

interface FilterOption {
  value: string;
  label: string;
  count?: number;
  disabled?: boolean;
}

type FilterValue = string | string[] | { min?: number; max?: number } | { start?: Date; end?: Date } | boolean | null;
```

---

## Slots

| Slot | Required | Description |
|------|----------|-------------|
| `header` | No | Custom header (title, actions) |
| `filter` | No | Custom filter rendering |
| `footer` | No | Apply/Reset buttons |

---

## State

| State | Trigger | Visual |
|-------|---------|--------|
| `expanded` | Default | Full panel |
| `collapsed` | Toggle | Minimized to header |
| `loading` | Async options | Skeleton per filter |
| `active` | Has values | Count badge, highlight |
| `empty` | No filters | "No filters available" |

---

## Accessibility

- **Role**: `aside` with `aria-label="Filters"`
- **Groups**: `fieldset` with `legend` per filter
- **Inputs**: Proper labels, `aria-describedby` for help
- **Keyboard**: Tab through filters, arrows within

---

## Keyboard

| Key | Action |
|-----|--------|
| `Tab` | Next filter |
| `Shift+Tab` | Previous filter |
| `Arrow Keys` | Within select/range |
| `Escape` | Close dropdown / Collapse |
| `Enter` | Toggle boolean / Apply date |

---

## Loading

- **Async Options**: Spinner in filter header
- **Apply**: Disable during submission

---

## Errors

- **Invalid Range**: Red border on min/max
- **Required**: Red asterisk
- **Network**: Toast notification

---

## Mobile

- **< 1024px**: Collapsible drawer from right
- **Trigger**: Filter button in toolbar (shows active count)
- **Apply**: Auto-closes drawer
- **Swipe**: Swipe right to close

---

## Permissions

| Role | Access |
|------|--------|
| All authenticated | ✅ |

---

## Telemetry

| Event | Properties |
|-------|------------|
| `filter_change` | `filter_key`, `value`, `type` |
| `filter_clear` | `filter_key` |
| `filter_clear_all` | `active_count` |
| `filter_collapse` | `collapsed` |

---

## React Query

```typescript
// Async filter options
const { data: agencies } = useQuery({
  queryKey: ['filters', 'agencies'],
  queryFn: () => fetchAgencies(),
  staleTime: 5 * 60 * 1000
});

// Persisted filter state
const [filters, setFilters] = useLocalStorage('discovery_filters', defaultFilters);
```

---

## Dependencies

- `Select` (options)
- `RangeSlider` (numeric ranges)
- `DatePicker` (date ranges)
- `Checkbox` (boolean)
- `Chips` (active multi-select)
- `Collapsible` (group collapse)
- `Badge` (active count)
- `lucide-react`: `Filter`, `X`, `Sliders`, `ChevronDown`, `ChevronUp`, `Check`, `X`, `Calendar`, `DollarSign`, `Hash`

---

## Usage Examples

```tsx
const filters = [
  {
    key: 'agency',
    label: 'Agency',
    type: 'multi-select',
    searchable: true,
    options: agencyOptions,
    group: 'Organization'
  },
  {
    key: 'zone',
    label: 'Zone',
    type: 'select',
    options: zoneOptions,
    group: 'Location'
  },
  {
    key: 'valueRange',
    label: 'Estimated Value',
    type: 'range',
    min: 0,
    max: 1_000_000_000,
    step: 1_000_000,
    unit: 'BDT',
    group: 'Financial'
  },
  {
    key: 'deadlineRange',
    label: 'Closing Date',
    type: 'date-range',
    group: 'Timeline'
  },
  {
    key: 'onlyActive',
    label: 'Active Only',
    type: 'boolean',
    group: 'Status'
  }
];

<FilterPanel
  filters={filters}
  values={filterValues}
  onChange={setFilterValues}
  onClear={clearFilters}
  showCount
/>
```

---

## Filter Value Patterns

```typescript
// Select: string | null
agency: 'BWDB' | null

// Multi-select: string[]
agency: ['BWDB', 'PWD'] | []

// Range: { min?: number, max?: number }
valueRange: { min: 10_000_000, max: 500_000_000 }

// Date Range: { start?: Date, end?: Date }
deadlineRange: { start: new Date('2026-01-01'), end: new Date('2026-12-31') }

// Boolean: boolean | null
onlyActive: true | false | null

// Text: string | null
keyword: 'bridge construction' | null
```

---

## Active Filter Chips

```
┌─────────────────────────────────────────────────┐
│ Filters (3)                    [Clear all]      │
├─────────────────────────────────────────────────┤
│ Agency: BWDB ✕  PWD ✕                          │
│ Zone: A ✕                                       │
│ Value: 10M – 500M BDT ✕                         │
├─────────────────────────────────────────────────┤
│ [Apply]                    [Reset]              │
└─────────────────────────────────────────────────┘
```

---

## Future Extensions

- [ ] Saved filter presets
- [ ] Filter dependencies (conditional)
- [ ] Filter templates
- [ ] Advanced query builder
- [ ] Export filter config
- [ ] Natural language filter input