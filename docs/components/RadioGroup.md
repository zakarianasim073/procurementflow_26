# RadioGroup Component Contract

**Package**: `shared/ui`  
**Type**: Form Input Component  
**Stability**: Stable  

---

## Purpose

Radio button group for single selection from mutually exclusive options. Used for agency selection, zone filtering, and mode switching.

---

## Props

```typescript
interface RadioGroupProps {
  /** Options */
  options: RadioOption[];
  /** Selected value */
  value: string | null;
  /** Change handler */
  onChange: (value: string) => void;
  /** Label */
  label?: string;
  /** Description */
  description?: string;
  /** Error message */
  error?: string;
  /** Direction */
  direction?: 'vertical' | 'horizontal'; // default: 'vertical'
  /** Required */
  required?: boolean;
  /** Disabled */
  disabled?: boolean;
  /** Custom className */
  className?: string;
}

interface RadioOption {
  value: string;
  label: string;
  description?: string;
  disabled?: boolean;
  icon?: React.ReactNode;
}
```

---

## Slots

| Slot | Required | Description |
|------|----------|-------------|
| `option` | No | Custom option rendering |

---

## State

| State | Trigger | Visual |
|-------|---------|--------|
| `default` | Initial | Unselected circles |
| `selected` | `value` matches | Filled dot, brand border |
| `hover` | Mouse enter | Subtle bg |
| `focus` | Keyboard | Ring outline |
| `disabled` | `disabled` | Muted, not clickable |
| `error` | `error` prop | Red border |

---

## Accessibility

- **Role**: `radiogroup` with `role="radio"` options
- **ARIA**: `aria-required`, `aria-invalid`
- **Labels**: `aria-labelledby` for group label
- **Keyboard**: Arrow keys navigate

---

## Keyboard

| Key | Action |
|-----|--------|
| `Tab` | Focus group |
| `Arrow Up/Down` | Previous/Next (vertical) |
| `Arrow Left/Right` | Previous/Next (horizontal) |
| `Space` / `Enter` | Select |
| `Home` / `End` | First/Last |

---

## Mobile

- **Vertical**: Default, stacked
- **Horizontal**: Scrollable on < 640px
- **Touch Target**: 44×44mm minimum

---

## Permissions

Not applicable

---

## Telemetry

| Event | Properties |
|-------|------------|
| `radio_select` | `value`, `label`, `group` |

---

## Usage Examples

```tsx
// Basic vertical
<RadioGroup
  label="Agency"
  value={agency}
  onChange={setAgency}
  options={[
    { value: 'BWDB', label: 'BWDB', description: 'Bangladesh Water Development Board' },
    { value: 'PWD', label: 'PWD', description: 'Public Works Department' },
    { value: 'LGED', label: 'LGED', description: 'Local Government Engineering Department' },
  ]}
/>

// Horizontal
<RadioGroup
  label="View Mode"
  value={viewMode}
  onChange={setViewMode}
  direction="horizontal"
  options={[
    { value: 'list', label: 'List', icon: <List /> },
    { value: 'grid', label: 'Grid', icon: <Grid /> },
    { value: 'map', label: 'Map', icon: <MapPin /> },
  ]}
/>

// With descriptions
<RadioGroup
  label="Comparison Mode"
  value={mode}
  onChange={setMode}
  options={[
    { value: 'quick', label: 'Quick Compare', description: 'Side-by-side rates only' },
    { value: 'detailed', label: 'Detailed Analysis', description: 'Full rate breakdown with margins' },
    { value: 'executive', label: 'Executive Summary', description: 'High-level recommendations' },
  ]}
/>

// With error
<RadioGroup
  label="Zone"
  value={zone}
  onChange={setZone}
  error="Please select a zone"
  options={zoneOptions}
/>

// With icons
<RadioGroup
  label="Export Format"
  value={format}
  onChange={setFormat}
  options={[
    { value: 'xlsx', label: 'Excel', icon: <FileSpreadsheet /> },
    { value: 'pdf', label: 'PDF', icon: <FileText /> },
    { value: 'docx', label: 'Word', icon: <FileDoc /> },
  ]}
/>
```

---

## Future Extensions

- [ ] Card-style options
- [ ] Image-based options
- [ ] Keyboard shortcut hints
- [ ] Option groups