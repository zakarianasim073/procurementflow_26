# Collapse Component Contract

**Package**: `shared/ui`  
**Type**: Disclosure Component  
**Stability**: Stable  

---

## Purpose

Simple show/hide wrapper for progressive disclosure. Used for advanced options, additional details, and "read more" patterns.

---

## Props

```typescript
interface CollapseProps {
  /** Open state */
  open?: boolean;
  /** Default open (uncontrolled) */
  defaultOpen?: boolean;
  /** Change handler */
  onChange?: (open: boolean) => void;
  /** Header/trigger */
  trigger: React.ReactNode;
  /** Content */
  children: React.ReactNode;
  /** Animation duration (ms) */
  duration?: number; // default: 200
  /** Show arrow icon */
  showArrow?: boolean; // default: true
  /** Custom className */
  className?: string;
}
```

---

## Slots

| Slot | Required | Description |
|------|----------|-------------|
| `trigger` | **Yes** | Clickable header |
| `children` | **Yes** | Collapsible content |

---

## State

| State | Trigger | Visual |
|-------|---------|--------|
| `closed` | Default/controlled | Arrow down, content hidden |
| `open` | Click/controlled | Arrow up, content visible |
| `animating` | Transition | Height transition |
| `disabled` | `disabled` prop | Muted trigger |

---

## Accessibility

- **Trigger**: `button` with `aria-expanded`, `aria-controls`
- **Content**: `div` with `role="region"`, `id` matches `aria-controls`
- **Hidden**: `hidden` attribute when closed

---

## Keyboard

| Key | Action |
|-----|--------|
| `Tab` | Focus trigger |
| `Enter` / `Space` | Toggle |

---

## Mobile

- **Touch**: Tap to toggle
- **Animation**: Smooth height transition

---

## Permissions

Not applicable

---

## Telemetry

| Event | Properties |
|-------|------------|
| `collapse_toggle` | `open` |

---

## Usage Examples

```tsx
// Basic
<Collapse trigger={<Text weight="medium">Show advanced options</Text>}>
  <AdvancedOptionsPanel />
</Collapse>

// Controlled
<Collapse
  open={showAdvanced}
  onChange={setShowAdvanced}
  trigger={<Button variant="ghost">Advanced</Button>}
>
  <AdvancedSettings />
</Collapse>

// Without arrow
<Collapse
  showArrow={false}
  trigger={<Text className="hover:underline">Read more</Text>}
>
  <LongDescription />
</Collapse>

// With custom trigger
<Collapse
  trigger={
    <Flex align="center" justify="between">
      <Text>Filters</Text>
      <Badge variant="outline">{activeCount} active</Badge>
    </Flex>
  }
>
  <FilterPanel />
</Collapse>
```

---

## Future Extensions

- [ ] Horizontal collapse (width animation)
- [ ] Multiple content sections
- [ ] Nested collapse support