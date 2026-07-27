# Badge Component Contract

**Package**: `shared/ui`  
**Type**: Status/Label Component  
**Stability**: Stable  

---

## Purpose

Small status indicator for counts, states, categories, and labels. Used in tables, cards, navigation, and inline with text.

---

## Props

```typescript
interface BadgeProps {
  /** Badge content */
  children: React.ReactNode;
  /** Visual variant */
  variant?: 'default' | 'primary' | 'success' | 'warning' | 'danger' | 'info' | 'outline';
  /** Size */
  size?: 'sm' | 'md' | 'lg';
  /** Rounded style */
  rounded?: 'sm' | 'md' | 'full';
  /** Show dot indicator */
  dot?: boolean;
  /** Dot color (when dot=true) */
  dotColor?: 'default' | 'success' | 'warning' | 'danger' | 'info';
  /** Removable */
  removable?: boolean;
  onRemove?: () => void;
  /** Custom className */
  className?: string;
}
```

---

## Variants

| Variant | Background | Text | Border | Use Case |
|---------|------------|------|--------|----------|
| `default` | `gray-100` | `gray-700` | None | Neutral labels |
| `primary` | `brand-100` | `brand-700` | None | Primary categories |
| `success` | `green-100` | `green-700` | None | Completed, active |
| `warning` | `amber-100` | `amber-700` | None | Pending, caution |
| `danger` | `red-100` | `red-700` | None | Errors, critical |
| `info` | `blue-100` | `blue-700` | None | Informational |
| `outline` | Transparent | `gray-700` | `gray-300` | Subtle labels |

---

## Sizes

| Size | Padding | Font | Height | Use Case |
|------|---------|------|--------|----------|
| `sm` | `2px 6px` | `text-xs` | 18px | Inline, dense |
| `md` | `2px 8px` | `text-xs` | 20px | Default |
| `lg` | `4px 10px` | `text-sm` | 24px | Prominent |

---

## State

| State | Visual |
|-------|--------|
| `default` | Variant styles |
| `hover` (removable) | Darker bg, x highlight |
| `focus` | Ring outline |

---

## Accessibility

- **Role**: `label` or `status`
- **Removable**: `button` with `aria-label="Remove [label]"`
- **Color**: Not color-only (always has text)

---

## Loading

Not applicable

---

## Errors

Not applicable

---

## Keyboard

| Key | Action |
|-----|--------|
| `Tab` | Focus (removable) |
| `Enter` / `Space` | Remove |

---

## Mobile

- **Touch**: 44×44mm hit area for removable
- **Sizes**: Scaled down 1 step on < 640px

---

## Permissions

Not applicable

---

## Telemetry

| Event | Properties |
|-------|------------|
| `badge_remove` | `label`, `variant` |

---

## React Query

Not applicable

---

## Dependencies

- `lucide-react`: `X` (remove)

---

## Usage Examples

```tsx
// Status badges
<Badge variant="success">Active</Badge>
<Badge variant="warning">Pending</Badge>
<Badge variant="danger">Failed</Badge>

// With dot
<Badge variant="success" dot>Online</Badge>
<Badge variant="danger" dotColor="danger">Offline</Badge>

// Count badge
<Badge variant="primary" size="sm">42</Badge>

// Removable (tags)
<Badge 
  variant="outline" 
  removable 
  onRemove={() => handleRemove(tag)}
>
  {tag}
</Badge>

// In table
<TableCell>
  <Badge variant={status === 'active' ? 'success' : 'warning'}>
    {status}
  </Badge>
</TableCell>

// Outline variant
<Badge variant="outline">BWDB</Badge>
<Badge variant="outline">Zone A</Badge>
```

---

## Future Extensions

- [ ] Pulse animation for live status
- [ ] Gradient variants
- [ ] Icon support (left/right)
- [ ] Clickable variant (link style)
- [ ] Group component (badge group)