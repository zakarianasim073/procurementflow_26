# Tooltip Component Contract

**Package**: `shared/ui`  
**Type**: Overlay Component  
**Stability**: Stable  

---

## Purpose

Contextual tooltip for additional information on hover/focus. Supports rich content, custom positioning, and delayed show/hide.

---

## Props

```typescript
interface TooltipProps {
  /** Tooltip content */
  content: React.ReactNode;
  /** Trigger element */
  children: React.ReactElement;
  /** Position */
  placement?: 'top' | 'bottom' | 'left' | 'right' | 'top-start' | 'top-end' | 'bottom-start' | 'bottom-end';
  /** Show delay (ms) */
  delayShow?: number; // default: 200
  /** Hide delay (ms) */
  delayHide?: number; // default: 100
  /** Disable hover */
  disableHover?: boolean;
  /** Disable focus */
  disableFocus?: boolean;
  /** Custom className */
  className?: string;
  /** Arrow */
  showArrow?: boolean; // default: true
  /** Offset */
  offset?: number; // default: 8
}
```

---

## Slots

| Slot | Required | Description |
|------|----------|-------------|
| — | — | Wraps single child element |

---

## State

| State | Trigger | Visual |
|-------|---------|--------|
| `hidden` | Default | Not rendered |
| `showing` | After delay | Fade in + slide |
| `visible` | Hover/Focus | Full opacity |
| `hiding` | Leave/Blur | Fade out |

---

## Accessibility

- **Role**: `tooltip` with `aria-describedby`
- **Trigger**: `aria-describedby` linking to tooltip ID
- **Keyboard**: Focus triggers show
- **Screen Reader**: Announces on focus

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
| `Tab` | Focus trigger → show |
| `Escape` | Hide (when focused) |

---

## Mobile

- **Touch**: Long press (500ms) to show
- **Dismiss**: Tap outside
- **Position**: Prefer bottom on mobile

---

## Permissions

Not applicable

---

## Telemetry

| Event | Properties |
|-------|------------|
| `tooltip_show` | `trigger_type` |
| `tooltip_hide` | `duration_ms` |

---

## React Query

Not applicable

---

## Dependencies

- `Popper` (positioning)
- `Transition` (animations)
- `lucide-react`: `Info` (default icon)

---

## Usage Examples

```tsx
// Basic
<Tooltip content="This tender is in evaluation phase">
  <Badge variant="warning">Under Review</Badge>
</Tooltip>

// With rich content
<Tooltip
  content={
    <Flex flexDir="column" gap={1}>
      <span className="font-medium">Tender 1298004</span>
      <span className="text-sm text-muted">BWDB • Zone A</span>
      <span className="text-sm">Closes: Jan 15, 2025</span>
    </Flex>
  }
>
  <span className="text-primary hover:underline">Tender 1298004</span>
</Tooltip>

// Custom delay
<Tooltip content="Copied to clipboard" delayShow={0} delayHide={500}>
  <Button variant="ghost" size="icon" onClick={copy}>
    <Copy />
  </Button>
</Tooltip>

// Disabled hover (focus only)
<Tooltip content="Keyboard users see this" disableHover>
  <Button variant="link">Keyboard Shortcut</Button>
</Tooltip>

// No arrow
<Tooltip content="Bottom centered" placement="bottom" showArrow={false}>
  <span>Hover me</span>
</Tooltip>
```

---

## Placement Examples

```
Top:        [tooltip]           Bottom:     [trigger]
             ▼                        ▲
          [trigger]                 [tooltip]

Left:    [tooltip] → [trigger]     Right:   [trigger] → [tooltip]
```

---

## Future Extensions

- [ ] Virtualized tooltips (for lists)
- [ ] Tooltip groups (shared delay)
- [ ] Follow cursor mode
- [ ] Rich content with actions
- [ ] Auto-hide on scroll