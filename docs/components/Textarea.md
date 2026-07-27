# Textarea Component Contract

**Package**: `shared/ui`  
**Type**: Form Input Component  
**Stability**: Stable  

---

## Purpose

Multi-line text input for descriptions, comments, and long-form content. Supports auto-resize, character count, and validation.

---

## Props

```typescript
interface TextareaProps extends Omit<React.TextareaHTMLAttributes<HTMLTextAreaElement>, 'onChange'> {
  /** Label */
  label?: string;
  /** Helper text */
  helperText?: string;
  /** Error message */
  error?: string;
  /** Placeholder */
  placeholder?: string;
  /** Value */
  value: string;
  /** Change handler */
  onChange: (value: string) => void;
  /** Auto-resize */
  autoResize?: boolean; // default: true
  /** Min rows */
  minRows?: number; // default: 3
  /** Max rows */
  maxRows?: number; // default: 10
  /** Character limit */
  maxLength?: number;
  /** Show character count */
  showCount?: boolean;
  /** Disabled */
  disabled?: boolean;
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
| — | — | Self-contained |

---

## State

| State | Trigger | Visual |
|-------|---------|--------|
| `default` | Initial | Border gray-300 |
| `hover` | Mouse enter | Border gray-400 |
| `focus` | Click/Tab | Ring brand-500 |
| `filled` | Has value | Label floats (optional) |
| `error` | `error` prop | Border red-500, red helper |
| `disabled` | `disabled` | BG gray-100, cursor not-allowed |
| `count-warning` | Near maxLength | Amber count |

---

## Accessibility

- **Label**: `<label htmlFor>` linked to textarea
- **Error**: `aria-invalid="true"`, `aria-describedby` error ID
- **Helper**: `aria-describedby` helper ID
- **Required**: `aria-required`
- **MaxLength**: Announces remaining characters

---

## Keyboard

| Key | Action |
|-----|--------|
| `Tab` | Focus |
| `Enter` | New line |
| `Shift+Enter` | New line (or submit if configured) |
| `Ctrl+Enter` | Submit (if configured) |
| `Escape` | Blur |

---

## Mobile

- **Font Size**: 16px prevents zoom
- **Auto-resize**: Smooth height animation
- **Keyboard**: Opens on focus

---

## Permissions

Not applicable

---

## Telemetry

| Event | Properties |
|-------|------------|
| `textarea_change` | `length`, `at_max` |
| `textarea_blur` | `valid`, `length` |

---

## Usage Examples

```tsx
// Basic
<Textarea
  label="Description"
  placeholder="Enter tender description..."
  value={description}
  onChange={setDescription}
  minRows={4}
/>

// With character limit
<Textarea
  label="Executive Summary"
  value={summary}
  onChange={setSummary}
  maxLength={500}
  showCount
  helperText="Max 500 characters"
/>

// Auto-resize with max
<Textarea
  label="Notes"
  value={notes}
  onChange={setNotes}
  autoResize
  minRows={3}
  maxRows={8}
/>

// Error state
<Textarea
  label="Remarks"
  value={remarks}
  onChange={setRemarks}
  error="Remarks are required for rejection"
/>

// Disabled
<Textarea
  label="System Notes"
  value={systemNotes}
  disabled
  helperText="Auto-generated"
/>
```

---

## Future Extensions

- [ ] Rich text toolbar
- [ ] Markdown preview
- [ ] @mentions autocomplete
- [ ] Spell check integration
- [ ] Voice input button