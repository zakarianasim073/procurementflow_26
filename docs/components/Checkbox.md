# Checkbox Component Contract

**Package**: `shared/ui`  
**Type**: Form Input Component  
**Stability**: Stable  

---

## Purpose

Checkbox input for boolean values, multi-select options, and agreement confirmations. Supports indeterminate state for "select all" patterns.

---

## Props

```typescript
interface CheckboxProps extends Omit<React.InputHTMLAttributes<HTMLInputElement>, 'type'> {
  /** Label */
  label?: string;
  /** Description */
  description?: string;
  /** Indeterminate state */
  indeterminate?: boolean;
  /** Size */
  size?: 'sm' | 'md' | 'lg';
  /** Required */
  required?: boolean;
  /** Custom className */
  className?: string;
}
```

---

## Slots

| Slot | Required | Description |
|------|----------|-------------|
| `label` | No | Custom label content |
| `description` | No | Custom description |

---

## State

| State | Trigger | Visual |
|-------|---------|--------|
| `unchecked` | Default | Empty box |
| `checked` | `checked=true` | Checkmark, brand bg |
| `indeterminate` | `indeterminate=true` | Minus line, brand bg |
| `hover` | Mouse enter | Subtle bg |
| `focus` | Keyboard | Ring outline |
| `disabled` | `disabled=true` | Muted, not clickable |
| `error` | `aria-invalid` | Red border |

---

## Accessibility

- **Role**: `checkbox`
- **ARIA**: `aria-checked`, `aria-required`, `aria-describedby`
- **Label**: `<label htmlFor>` or `aria-label`
- **Keyboard**: Space toggles

---

## Keyboard

| Key | Action |
|-----|--------|
| `Tab` | Focus |
| `Space` | Toggle |
| `Enter` | Toggle (if in form) |

---

## Usage Examples

```tsx
// Basic
<Checkbox
  label="I agree to terms"
  onChange={setAgreed}
/>

// With description
<Checkbox
  label="Subscribe to newsletter"
  description="We'll send weekly updates"
  onChange={setSubscribed}
/>

// Indeterminate (select all)
<Checkbox
  indeterminate={someSelected && !allSelected}
  checked={allSelected}
  label="Select all"
  onChange={handleSelectAll}
/>

// Error state
<Checkbox
  label="Required field"
  error={!agreed && submitted}
  onChange={setAgreed}
/>

// Group
<CheckboxGroup
  label="Agencies"
  options={[
    { value: 'BWDB', label: 'BWDB' },
    { value: 'PWD', label: 'PWD' },
    { value: 'LGED', label: 'LGED' }
  ]}
  value={selected}
  onChange={setSelected}
/>
```

---

## CheckboxGroup Props

```typescript
interface CheckboxGroupProps {
  label: string;
  description?: string;
  options: { value: string; label: string; disabled?: boolean }[];
  value: string[];
  onChange: (value: string[]) => void;
  direction?: 'vertical' | 'horizontal';
  required?: boolean;
  error?: string;
}
```

---

## Future Extensions

- [ ] Custom checkmark icons
- [ ] Toggle switch variant
- [ ] Keyboard shortcut hints