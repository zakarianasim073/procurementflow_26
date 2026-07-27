# Button Component Contract

**Package**: `shared/ui`  
**Type**: Action Component  
**Stability**: Stable  

---

## Purpose

Primary action trigger with multiple variants, sizes, and states. Core interaction primitive for forms, dialogs, toolbars, and cards.

---

## Props

```typescript
interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  /** Visual variant */
  variant?: 'primary' | 'secondary' | 'outline' | 'ghost' | 'destructive' | 'link';
  /** Size */
  size?: 'sm' | 'md' | 'lg' | 'icon';
  /** Loading state */
  loading?: boolean;
  /** Disable ripple (mobile) */
  disableRipple?: boolean;
  /** Full width */
  fullWidth?: boolean;
  /** Left icon */
  leftIcon?: React.ReactNode;
  /** Right icon */
  rightIcon?: React.ReactNode;
  /** Custom className */
  className?: string;
}
```

---

## Variants

| Variant | Background | Text | Border | Use Case |
|---------|------------|------|--------|----------|
| `primary` | `brand-600` | White | None | Main CTA |
| `secondary` | `gray-100` | `gray-900` | `gray-300` | Secondary action |
| `outline` | Transparent | `brand-600` | `brand-600` | Tertiary action |
| `ghost` | Transparent | `gray-700` | None | Subtle action |
| `destructive` | `red-600` | White | None | Delete/danger |
| `link` | Transparent | `brand-600` | None | Inline/link style |

---

## Sizes

| Size | Padding | Font | Height | Icon |
|------|---------|------|--------|------|
| `sm` | `6px 12px` | `text-xs` | 28px | 14px |
| `md` | `8px 16px` | `text-sm` | 36px | 16px |
| `lg` | `12px 24px` | `text-base` | 44px | 20px |
| `icon` | `8px` | — | 36px | 18px |

---

## States

| State | Visual |
|-------|--------|
| `default` | Base variant styles |
| `hover` | Darken bg / darker border |
| `active` | Darken further, scale 0.98 |
| `focus` | Ring `brand-500` (2px) |
| `loading` | Spinner, disabled, same width |
| `disabled` | Opacity 0.5, cursor not-allowed |

---

## Accessibility

- **Role**: `button`
- **Loading**: `aria-busy="true"`, `aria-disabled="true"`
- **Disabled**: `aria-disabled="true"`
- **Focus**: Visible ring
- **Keyboard**: Enter/Space activates

---

## Keyboard

| Key | Action |
|-----|--------|
| `Tab` | Focus |
| `Enter` / `Space` | Click |
| `Escape` | No action (unless in dialog) |

---

## Mobile

- **Min Height**: 44dp (all sizes)
- **Touch Target**: 44×44dp minimum
- **Ripple**: Native ripple on press (can disable)
- **Loading**: Spinner centered, text hidden

---

## Permissions

Not applicable

---

## Telemetry

| Event | Properties |
|-------|------------|
| `button_click` | `variant`, `size`, `label`, `loading` |

---

## React Query

Not applicable

---

## Dependencies

- `lucide-react`: `Loader2` (loading)
- `clsx`, `tailwind-merge`

---

## Usage Examples

```tsx
// Primary CTA
<Button variant="primary" onClick={handleSubmit}>
  Submit Tender
</Button>

// With icons
<Button variant="secondary" leftIcon={<Download />}>
  Export Excel
</Button>

// Loading state
<Button variant="primary" loading>
  Processing...
</Button>

// Destructive
<Button variant="destructive" onClick={handleDelete}>
  Delete Tender
</Button>

// Icon button
<Button variant="ghost" size="icon" aria-label="Settings">
  <Settings />
</Button>

// Full width
<Button variant="primary" fullWidth>
  Save Changes
</Button>

// Link style
<Button variant="link" onClick={handleCancel}>
  Cancel
</Button>
```

---

## Future Extensions

- [ ] Button group (toggle, radio)
- [ ] Split button (dropdown)
- [ ] Progress button (inline progress)
- [ ] Floating action button (FAB)
- [ ] Keyboard shortcut hint