# Select Component Contract

**Package**: `shared/ui`  
**Type**: Form Input Component  
**Stability**: Stable  

---

## Purpose

Accessible select dropdown with search, multi-select, grouping, async options, and custom rendering. Used throughout forms for agency, zone, tender, contractor selection.

---

## Props

```typescript
interface SelectProps<T = string> {
  /** Selected value(s) */
  value: T | T[] | null;
  /** Change handler */
  onChange: (value: T | T[] | null) => void;
  /** Options */
  options: SelectOption<T>[];
  /** Placeholder */
  placeholder?: string;
  /** Multiple selection */
  multiple?: boolean;
  /** Searchable */
  searchable?: boolean;
  /** Grouped options */
  grouped?: boolean;
  /** Async options */
  async?: boolean;
  /** Load options function */
  loadOptions?: (query: string) => Promise<SelectOption<T>[]>;
  /** Loading state */
  loading?: boolean;
  /** Error state */
  error?: string;
  /** Disabled */
  disabled?: boolean;
  /** Required */
  required?: boolean;
  /** Label */
  label?: string;
  /** Helper text */
  helperText?: string;
  /** Custom option renderer */
  renderOption?: (option: SelectOption<T>, selected: boolean) => React.ReactNode;
  /** Custom value renderer */
  renderValue?: (value: T | T[]) => React.ReactNode;
  /** Clearable */
  clearable?: boolean;
  /** Max selected (multiple) */
  maxSelected?: number;
  /** Custom className */
  className?: string;
}

interface SelectOption<T> {
  value: T;
  label: string;
  description?: string;
  icon?: React.ReactNode;
  disabled?: boolean;
  group?: string;
  metadata?: Record<string, any>;
}
```

---

## Slots

| Slot | Required | Description |
|------|----------|-------------|
| `prefix` | No | Prefix content (e.g., icon) |
| `suffix` | No | Suffix content (e.g., loading) |
| `option` | No | Custom option rendering |
| `groupHeader` | No | Group header rendering |
| `empty` | No | Empty state |
| `loading` | No | Loading state |

---

## State

| State | Trigger | Visual |
|-------|---------|--------|
| `closed` | Default | Border, placeholder |
| `open` | Click/Focus | Dropdown open |
| `searching` | Typing in search | Loading in options |
| `loading` | `loading=true` / async | Spinner in trigger |
| `error` | `error` prop | Red border, message |
| `disabled` | `disabled=true` | Muted, not clickable |
| `multiple` | `multiple=true` | Chips in trigger |

---

## Accessibility

- **Role**: `combobox` with `aria-expanded`, `aria-controls`
- **Listbox**: `role="listbox"` with `role="option"` items
- **Search**: `aria-autocomplete="list"` on input
- **Selected**: `aria-selected` on options
- **Live Region**: Search results announced
- **Keyboard**: Full keyboard navigation
- **Screen Reader**: Announces selection, count, groups

---

## Keyboard

| Key | Action |
|-----|--------|
| `Tab` | Focus trigger |
| `Enter` / `Space` | Open/Close |
| `Arrow Down` | Open / Next option |
| `Arrow Up` | Previous option |
| `Home` / `End` | First/Last option |
| `Type` | Search filter |
| `Enter` | Select option |
| `Escape` | Close |
| `Backspace` | Remove chip (multiple) |
| `Ctrl+A` | Select all (multiple) |

---

## Loading State

- **Trigger**: Spinner replaces chevron
- **Options**: Skeleton items
- **Async**: Debounced search (300ms)

---

## Error State

- **Trigger**: Red border, shake animation
- **Message**: Below trigger, `role="alert"`
- **Clear**: On focus/change

---

## Mobile

- **< 640px**: Full-screen bottom sheet
- **Search**: Fixed header in sheet
- **Groups**: Collapsible sections
- **Selected**: Checkmarks, sticky selected at top

---

## Permissions

Not applicable (form input)

---

## Telemetry

| Event | Properties |
|-------|------------|
| `select_open` | `option_count`, `searchable` |
| `select_select` | `value`, `label`, `group` |
| `select_search` | `query`, `results_count` |
| `select_clear` | `previous_value` |

---

## React Query

```typescript
// Async options with React Query
const { data: zones } = useQuery({
  queryKey: ['zones', searchQuery],
  queryFn: () => fetchZones(searchQuery),
  enabled: searchQuery.length >= 2
});

<Select
  async
  loadOptions={(query) => fetchZones(query)}
  options={zones || []}
/>
```

---

## Dependencies

- `Popover` (dropdown)
- `VirtualList` (options virtualization)
- `Input` (search)
- `Checkbox` (multiple)
- `lucide-react`: `ChevronDown`, `Search`, `X`, `Check`, `Loader2`, `FolderOpen`, `Tag`

---

## Usage Examples

```tsx
// Basic
<Select
  value={zone}
  onChange={setZone}
  options={[
    { value: 'A', label: 'Zone A' },
    { value: 'B', label: 'Zone B' },
  ]}
  placeholder="Select zone"
/>

// Multiple with chips
<Select
  multiple
  value={selectedAgencies}
  onChange={setSelectedAgencies}
  options={agencyOptions}
  placeholder="Select agencies"
  maxSelected={5}
  renderValue={(values) => (
    <Flex wrap gap={2}>
      {values.map(v => <Badge key={v}>{v}</Badge>)}
    </Flex>
  )
/>

// Grouped
<Select
  grouped
  value={tenderType}
  onChange={setTenderType}
  options={[
    { value: 'works', label: 'Works', group: 'Category' },
    { value: 'goods', label: 'Goods', group: 'Category' },
    { value: 'services', label: 'Services', group: 'Category' },
    { value: 'bwdb', label: 'BWDB', group: 'Agency' },
    { value: 'pwd', label: 'PWD', group: 'Agency' },
  ]}
/>

// Async search
<Select
  async
  searchable
  loadOptions={async (query) => {
    const res = await fetch(`/api/contractors?q=${query}`);
    return res.json();
  }}
  placeholder="Search contractors..."
  renderOption={(opt, selected) => (
    <Flex align="center" gap={2}>
      <Badge variant={opt.metadata?.type}>{opt.metadata?.type}</Badge>
      <span>{opt.label}</span>
    </Flex>
  )}
/>

// Custom option rendering
<Select
  options={contractorOptions}
  renderOption={(opt, selected) => (
    <Flex align="center" gap={2} className={cn(selected && 'bg-primary/10')}>
      <Avatar src={opt.metadata?.logo} fallback={opt.label[0]} />
      <Flex flexDir="column">
        <span>{opt.label}</span>
        <span className="text-xs text-muted">{opt.metadata?.district}</span>
      </span>
    </Flex>
  )}
/>
```

---

## Future Extensions

- [ ] Tagging (create new options)
- [ ] Creatable async options
- [ ] Option templates
- [ ] Drag-drop reorder (multiple)
- [ ] Keyboard shortcuts for groups
- [ ] Option pagination (infinite scroll)