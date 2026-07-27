# Popover Component Contract

**Module:** `shared/ui/Popover`
**Layer:** shared
**Version:** 1.0.0
**Status:** Draft

## Purpose
Floating content container positioned relative to a trigger element, used for filters, detail previews, and contextual information without navigating away from the current view.

## Props
```typescript
interface PopoverProps {
  trigger: ReactNode;
  children: ReactNode;
  placement?: Placement;
  align?: 'start' | 'center' | 'end';
  offset?: number;
  open?: boolean;
  defaultOpen?: boolean;
  onOpenChange?: (open: boolean) => void;
  triggerType?: 'click' | 'hover' | 'focus';
  closeOnClickOutside?: boolean;
  closeOnEscape?: boolean;
  hoverDelay?: number;
  contentClassName?: string;
  arrow?: boolean;
  modal?: boolean;
  testId?: string;
}

interface PopoverContentProps {
  children: ReactNode;
  className?: string;
}
```

## Slots
- `trigger` — Element that toggles popover
- `content` — Floating popover body
- `arrow` — Optional arrow pointing to trigger
- `close` — Optional close button

## State
```typescript
interface PopoverState {
  isOpen: boolean;
  triggerRect: DOMRect | null;
  contentRect: DOMRect | null;
}
```

## Accessibility
- **ARIA:** `aria-haspopup="true"`, `aria-expanded`, `role="dialog"` for modal
- **Keyboard:** Enter/Space toggle, Escape closes, Tab traps focus in modal
- **Focus:** Auto-focus first focusable element on open, return focus to trigger on close

## Loading
- N/A — presentation-only

## Errors
- N/A — renders content as-is

## Keyboard
| Key | Action |
|-----|--------|
| Enter/Space | Toggle (click trigger) |
| Escape | Close popover |
| Tab | Move focus within popover |
| Shift+Tab | Reverse focus within popover |

## Mobile
- Full-width bottom sheet on screens <640px
- Backdrop overlay for modal popovers
- Swipe down to dismiss

## Permissions
- No restrictions

## Telemetry
- `popover.open` — Popover opened
- `popover.close` — Popover closed

## React Query
- None — stateless presentation component

## Dependencies
- Floating UI (`@floating-ui/react`) for positioning
- `shared/hooks/useClickOutside` for outside clicks
- `shared/hooks/useEscapeKey` for keyboard dismiss

## Future Extensions
- Animation presets (fade, scale, slide)
- Virtual scrolling for large popover content
- Nested popovers with stack management
