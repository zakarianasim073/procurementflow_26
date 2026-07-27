# Dropdown Component Contract

**Package**: `shared/ui`  
**Type**: Form Input Component  
**Stability**: Stable  

---

## Purpose

Dropdown select with search, groups, async loading, and custom rendering. Enhanced version of native select for complex data.

---

## Props

```typescript
interface DropdownProps<T = string> {
  /** Selected value(s) */
  value: T | T[] | null;
  /** Change handler */
  onChange: (value: T | T[] | null) => void;
  /** Options */
  options: DropdownOption<T>[];
  /** Placeholder */
  placeholder?: string;
  /** Multiple selection */
  multiple?: boolean;
  /** Searchable */
  searchable?: boolean;
  /** Grouped options */
  grouped?: boolean;
  /** Async loading */
  async?: boolean;
  /** Load options function */
  loadOptions?: (query: string) => Promise<DropdownOption<T>[]>;
  /** Loading state */
  loading?: boolean;
  /** Error message */
  error?: string;
  /** Disabled */
  disabled?: boolean;
  /** Clearable */
  clearable?: boolean;
  /** Max selected (multiple) */
  maxSelected?: number;
  /** Custom option renderer */
  renderOption?: (option: DropdownOption<T>, selected: boolean) => React.ReactNode;
  /** Custom value renderer */
  renderValue?: (value: T | T[]) => React.ReactNode;
  /** Custom className */
  className?: string;
}

interface DropdownOption<T> {
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
| `prefix` | No | Leading content (icon) |
| `suffix` | No | Trailing content (clear, loader) |
| `option` | No | Custom option rendering |
| `groupHeader` | No | Group header rendering |
| `empty` | No | Empty state |
| `loading` | No | Loading state |

---

## State

| State | Trigger | Visual |
|-------|---------|--------|
| `closed` | Default | Trigger only |
| `open` | Click/Focus | Dropdown visible |
| `searching` | Typing | Loader in input |
| `loading` | `loading=true` | Spinner in trigger |
| `error` | `error` prop | Red border, message |
| `disabled` | `disabled=true` | Muted, not clickable |

---

## Accessibility

- **Role**: `combobox` with `aria-expanded`, `aria-controls`
- **Listbox**: `role="listbox"` with `role="option"` items
- **Search**: `aria-autocomplete="list"`
- **Selected**: `aria-selected`
- **Groups**: `role="group"` with `aria-labelledby`
- **Keyboard**: Full combobox pattern

---

## Keyboard

| Key | Action |
|-----|--------|
| `Tab` | Focus trigger |
| `Enter` / `Space` | Open/Close |
| `Arrow Down` | Open / Next option |
| `Arrow Up` | Previous option |
| `Home` / `End` | First/Last option |
| `Type` | Filter (searchable) |
| `Enter` | Select option |
| `Escape` | Close |
| `Backspace` | Remove last (multiple) |
| `Ctrl+A` | Select all (multiple) |

---

## Mobile

- **< 640px**: Full-screen bottom sheet
- **Search**: Fixed header in sheet
- **Groups**: Collapsible sections
- **Touch**: 44×44mm targets

---

## Permissions

Not applicable (form input)

---

## Telemetry

| Event | Properties |
|-------|------------|
| `dropdown_open` | `option_count`, `searchable` |
| `dropdown_select` | `value`, `label`, `group` |
| `dropdown_search` | `query`, `results` |
| `dropdown_clear` | `previous_value` |

---

## Usage Examples

```tsx
// Basic
<Dropdown
  value={agency}
  onChange={setAgency}
  options={[
    { value: 'BWDB', label: 'BWDB' },
    { value: 'PWD', label: 'PWD' },
    { value: 'LGED', label: 'LGED' }
  ]}
  placeholder="Select agency"
/>

// Searchable with groups
<Dropdown
  grouped
  searchable
  value={zone}
  onChange={setZone}
  options={[
    { value: 'A', label: 'Zone A', group: 'BWDB/PWD' },
    { value: 'B', label: 'Zone B', group: 'BWDB/PWD' },
    { value: 'C', label: 'Zone C (LGED=D)', group: 'LGED' },
    { value: 'D', label: 'Zone D (LGED=C)', group: 'LGED' }
  ]}
/>

// Multiple with chips
<Dropdown
  multiple
  value={selectedAgencies}
  onChange={setSelectedAgencies}
  options={agencyOptions}
  maxSelected={5}
  renderValue={(values) => (
    <Flex wrap gap={2}>
      {values.map(v => <Badge key={v} removable onRemove={() => remove(v)}>{v}</Badge>)}
    </Flex>
  )
/>

// Async search
<Dropdown
  async
  searchable
  loadOptions={async (query) => {
    const res = await fetch(`/api/contractors?q=${query}`);
    return res.json();
  }}
  placeholder="Search contractors..."
  renderOption={(opt, selected) => (
    <Flex align="center" gap={2} className={selected ? 'bg-primary/10' : ''}>
      <Avatar src={opt.metadata?.logo} fallback={opt.label[0]} />
      <Flex flexDir="column">
        <Text>{opt.label}</Text>
        <Text size="xs" className="text-muted">{opt.metadata?.district}</Text>
      </Flex>
    </Flex>
  )}
/>

// Custom option rendering
<Dropdown
  options={contractorOptions}
  renderOption={(opt, selected) => (
    <Flex align="center" gap={3} className={cn(selected && 'bg-primary/10')}>
      <Checkbox checked={selected} />
      <Flex flexDir="column">
        <Text weight={selected ? 'medium' : 'normal'}>{opt.label}</Text>
        <Text size="sm" className="text-muted">{opt.metadata?.type}</Text>
      </Text>
    </Flex>
  )}
/>
```

---

## Future Extensions

- [ ] Tagging (create new options)
- [ ] Virtualized list (1000+ options)
- [ ] Drag-drop reorder (multiple)
- [ ] Keyboard shortcuts for common options
- [ ] Option templates
- [ ] Server-side filtering hints