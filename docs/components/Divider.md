# Divider Component Contract

**Package**: `shared/ui`  
**Type**: Layout Component  
**Stability**: Stable  

---

## Purpose

Horizontal or vertical visual separator for grouping content, sections, and list items.

---

## Props

```typescript
interface DividerProps {
  /** Orientation */
  orientation?: 'horizontal' | 'vertical';
  /** Visual variant */
  variant?: 'solid' | 'dashed' | 'dotted' | 'gradient';
  /** Thickness */
  thickness?: 'thin' | 'medium' | 'thick';
  /** Label in center */
  label?: string;
  /** Label position */
  labelPosition?: 'left' | 'center' | 'right';
  /** Length (for vertical) */
  length?: string | number;
  /** Custom className */
  className?: string;
}
```

---

## Variants

| Variant | Style | Use Case |
|---------|-------|----------|
| `solid` | Solid line | Default sections |
| `dashed` | Dashed line | Subtle separation |
| `dotted` | Dotted line | Very subtle |
| `gradient` | Fade to transparent | Decorative |

---

## Sizes

| Thickness | Width | Use Case |
|-----------|-------|----------|
| `thin` | 1px | Default |
| `medium` | 2px | Emphasis |
| `thick` | 3px | Major sections |

---

## Slots

| Slot | Required | Description |
|------|----------|-------------|
| `label` | No | Custom label content |

---

## State

| State | Visual |
|-------|--------|
| `default` | Normal opacity |
| `subtle` | `opacity-50` (with `label`) |

---

## Accessibility

- **Role**: `separator` (ARIA)
- **Label**: `aria-orientation`
- **Vertical**: `aria-orientation="vertical"`

---

## Usage Examples

```tsx
// Basic horizontal
<Divider />

// With label
<Divider label="OR" />

// Vertical
<Divider orientation="vertical" length="100px" />

// Dashed
<Divider variant="dashed" />

// Gradient fade
<Divider variant="gradient" thickness="medium" />

// In list
<List>
  <ListItem>Item 1</ListItem>
  <Divider />
  <ListItem>Item 2</ListItem>
</List>
```

---

## Future Extensions

- [ ] Vertical label support
- [ ] Custom thickness (px)
- [ ] Pattern variants