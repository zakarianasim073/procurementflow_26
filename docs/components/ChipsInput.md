# ChipsInput Component Contract

**Package**: `shared/ui`  
**Type**: Form Input Component  
**Stability**: Stable  

---

## Purpose

Tokenized multi-select input for tags, categories, and entity selection with autocomplete and custom rendering.

---

## Props

```typescript
interface ChipsInputProps<T = string> {
  /** Selected values */
  value: T[];
  /** Change handler */
  onChange: (value: T[]) => void;
  /** Available options */
  options: ChipOption<T>[];
  /** Placeholder */
  placeholder?: string;
  /** Searchable */
  searchable?: boolean; // default: true
  /** Max chips */
  maxChips?: number;
  /** Allow custom entries */
  creatable?: boolean;
  /** Create label */
  createLabel?: string; // default: "Create"
  /** Min query length for create */
  minCreateLength?: number; // default: 1
  /** Disabled */
  disabled?: boolean;
  /** Error message */
  error?: string;
  /** Label */
  label?: string;
  /** Helper text */
  helperText?: string;
  /** Custom chip render */
  renderChip?: (option: ChipOption<T>, onRemove: () => void) => React.ReactNode;
  /** Custom option render */
  renderOption?: (option: ChipOption<T>, selected: boolean) => React.ReactNode;
  /** Custom className */
  className?: string;
}

interface ChipOption<T> {
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
| `chip` | No | Custom chip rendering |
| `option` | No | Custom dropdown option |
| `prefix` | No | Prefix in input |
| `suffix` | No | Clear button, etc. |

---

## State

| State | Trigger | Visual |
|-------|---------|--------|
| `default` | Initial | Chips + input |
| `focused` | Click/Tab | Ring outline, dropdown open |
| `searching` | Typing | Loader in suffix |
| `disabled` | `disabled` | Muted, no interaction |
| `error` | `error` prop | Red border, message |
| `max-reached` | `maxChips` hit | Hide input, show hint |

---

## Accessibility

- **Role**: `combobox` with `aria-controls`, `aria-expanded`
- **Listbox**: `role="listbox"` with `role="option"`
- **Chips**: `role="button"` with `aria-label="Remove [label]"`
- **Keyboard**: Full combobox pattern

---

## Keyboard

| Key | Action |
|-----|--------|
| `Tab` | Focus input |
| `Enter` | Select option / Create |
| `Escape` | Close dropdown |
| `Arrow Down/Up` | Navigate options |
| `Backspace` | Remove last chip (when input empty) |
| `Ctrl+A` | Select all chips |
| `Delete` | Remove focused chip |

---

## Mobile

- **Dropdown**: Bottom sheet on < 640px
- **Chips**: Horizontal scroll if many
- **Touch**: 44×44mm tap targets

---

## Usage Examples

```tsx
// Basic tags
<ChipsInput
  value={tags}
  onChange={setTags}
  options={[
    { value: 'bridge', label: 'Bridge' },
    { value: 'road', label: 'Road' },
    { value: 'building', label: 'Building' },
  ]}
  placeholder="Add tags..."
/>

// With descriptions and groups
<ChipsInput
  value={selectedAgencies}
  onChange={setSelectedAgencies}
  options={[
    { value: 'BWDB', label: 'BWDB', group: 'Water', description: 'Bangladesh Water Development Board' },
    { value: 'PWD', label: 'PWD', group: 'Roads', description: 'Public Works Department' },
    { value: 'LGED', label: 'LGED', group: 'Local Gov', description: 'Local Government Engineering Dept' },
  ]}
  grouped
  searchable
/>

// With descriptions and icons
<ChipsInput
  value={selectedContractors}
  onChange={setSelectedContractors}
  options={contractorOptions}
  renderOption={(opt, selected) => (
    <Flex align="center" gap={3} className={selected ? 'bg-primary/10' : ''}>
      <Avatar size="sm" name={opt.label} src={opt.metadata?.logo} />
      <Flex flexDir="column">
        <Text weight={selected ? 'medium' : 'normal'}>{opt.label}</Text>
        <Text size="xs" className="text-muted">{opt.description}</Text>
      </Flex>
    </Flex>
  )}
  renderChip={(opt, onRemove) => (
    <Badge variant="primary" removable onRemove={onRemove}>
      <Avatar size="xs" name={opt.label} src={opt.metadata?.logo} />
      {opt.label}
    </Badge>
  )}
/>

// Creatable (free-form tags)
<ChipsInput
  value={customTags}
  onChange={setCustomTags}
  options={suggestedTags}
  creatable
  createLabel="Add new tag"
  placeholder="Type to add tags..."
/>

// With max chips
<ChipsInput
  value={selectedZones}
  onChange={setSelectedZones}
  options={zoneOptions}
  maxChips={3}
  placeholder="Select up to 3 zones"
/>

// Error state
<ChipsInput
  value={requiredAgencies}
  onChange={setRequiredAgencies}
  options={agencyOptions}
  error="At least one agency is required"
  required
/>
```

---

## Custom Chip Rendering

```tsx
renderChip={(option, onRemove) => (
  <Badge
    variant="outline"
    removable
    onRemove={onRemove}
    className="gap-1"
  >
    <Avatar size="xs" name={option.label} src={option.metadata?.logo} />
    <span>{option.label}</span>
  </Badge>
)}

renderOption={(option, selected) => (
  <Flex align="center" gap={3} className={cn(
    'p-2 rounded',
    selected && 'bg-primary/10'
  )}>
    <Checkbox checked={selected} />
    <Flex flexDir="column">
      <Text weight="medium">{option.label}</Text>
      <Text size="sm" className="text-muted">{option.description}</Text>
    </Text>
  </Flex>
)}
```

---

## Future Extensions

- [ ] Virtualized options (1000+)
- [ ] Drag-drop reorder
- [ ] Keyboard shortcuts for common options
- [ ] Option templates
- [ ] Async validation on create