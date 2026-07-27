# Skeleton Component Contract

**Package**: `shared/ui`  
**Type**: Feedback Component  
**Stability**: Stable  

---

## Purpose

Placeholder loading state for content that hasn't loaded yet. Reduces perceived latency and prevents layout shift.

---

## Props

```typescript
interface SkeletonProps {
  /** Variant */
  variant?: 'text' | 'circular' | 'rectangular' | 'card' | 'avatar' | 'table-row';
  /** Width */
  width?: string | number;
  /** Height */
  height?: string | number;
  /** Number of lines (text variant) */
  lines?: number;
  /** Line spacing */
  lineSpacing?: number;
  /** Border radius */
  radius?: 'none' | 'sm' | 'md' | 'lg' | 'full';
  /** Animation */
  animation?: 'pulse' | 'wave' | 'none'; // default: 'pulse'
  /** Custom className */
  className?: string;
}
```

---

## Variants

| Variant | Use Case | Default Dimensions |
|---------|----------|-------------------|
| `text` | Paragraphs, labels | 100% × 1rem × lines |
| `circular` | Avatars, icons | 40×40 |
| `rectangular` | Images, cards | 100% × 120px |
| `card` | Full card | 100% × 200px |
| `avatar` | User avatars | 40×40 |
| `table-row` | Table rows | 100% × 48px |

---

## Slots

| Slot | Required | Description |
|------|----------|-------------|
| — | — | Self-contained |

---

## State

| State | Visual |
|-------|--------|
| `loading` | Animated shimmer |
| `loaded` | Hidden (replaced by content) |

---

## Accessibility

- **Role**: `status` with `aria-busy="true"`
- **Hidden**: `aria-hidden="true"` from screen readers
- **Live Region**: `aria-live="polite"` for completion

---

## Animation

| Type | Description |
|------|-------------|
| `pulse` | Opacity fade (default) |
| `wave` | Left-to-right shimmer |
| `none` | Static gray |

---

## Usage Examples

```tsx
// Text lines
<Skeleton variant="text" lines={3} width="80%" />

// Avatar
<Skeleton variant="circular" size="md" />

// Card
<Skeleton variant="card" height={200} />

// Table row
<Skeleton variant="table-row" />

// Custom dimensions
<Skeleton variant="rectangular" width="300px" height="200px" radius="lg" />

// Wave animation
<Skeleton variant="text" lines={5} animation="wave" />

// In card grid
<Grid cols={3} gap={4}>
  {[1,2,3].map(i => (
    <Skeleton key={i} variant="card" />
  ))}
</Grid>
```

---

## Composition Patterns

```tsx
// Skeleton card with image + text
<Card>
  <Skeleton variant="rectangular" height={150} radius="md" />
  <CardContent className="p-4 space-y-3">
    <Skeleton variant="text" width="60%" />
    <Skeleton variant="text" width="80%" />
    <Skeleton variant="text" width="40%" />
  </CardContent>
</Card>

// Table with header
<Table>
  <TableHeader>...</TableHeader>
  <TableBody>
    {[1,2,3].map(i => (
      <Skeleton key={i} variant="table-row" />
    ))}
  </TableBody>
</Table>
```

---

## Future Extensions

- [ ] Theme-aware colors (dark mode)
- [ ] Custom shimmer colors
- [ ] Staggered animation for lists