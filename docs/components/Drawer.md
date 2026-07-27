# Drawer Component Contract

**Module:** `shared/ui/Drawer`
**Layer:** shared
**Version:** 1.0.0
**Status:** Draft

## Purpose
Slide-in panel from screen edge for secondary content (tender details, filter panels, agent activity) that doesn't require full page navigation.

## Props
```typescript
interface DrawerProps {
  open: boolean;
  onClose: () => void;
  children: ReactNode;
  placement?: 'left' | 'right' | 'top' | 'bottom';
  size?: 'sm' | 'md' | 'lg' | 'xl' | number;
  title?: string;
  subtitle?: string;
  header?: ReactNode;
  footer?: ReactNode;
  closable?: boolean;
  maskClosable?: boolean;
  keyboard?: boolean;
  afterOpenChange?: (open: boolean) => void;
  className?: string;
  testId?: string;
}

interface DrawerHeaderProps {
  title: string;
  subtitle?: string;
  closable?: boolean;
  onClose?: () => void;
  extra?: ReactNode;
}

interface DrawerFooterProps {
  children: ReactNode;
  align?: 'left' | 'center' | 'right';
}
```

## Slots
- `header` — Title bar with close button
- `content` — Main scrollable body
- `footer` — Action bar (sticky at bottom)
- `close` — Custom close button

## State
```typescript
interface DrawerState {
  isVisible: boolean;
  isAnimating: boolean;
}
```

## Accessibility
- **ARIA:** `role="dialog"`, `aria-modal="true"`, `aria-labelledby` for title
- **Keyboard:** Escape closes, Tab traps focus
- **Focus:** Auto-focus drawer on open, restore focus to trigger on close
- **Focus trap:** Tab cycles through focusable elements within drawer

## Loading
- N/A — renders children directly

## Errors
- N/A — parent handles error states

## Keyboard
| Key | Action |
|-----|--------|
| Escape | Close drawer |
| Tab | Next focusable element |
| Shift+Tab | Previous focusable element |

## Mobile
- Full-screen on mobile (<640px)
- Swipe right to close (right placement)
- Swipe left to close (left placement)
- Swipe down to close (top/bottom)
- Backdrop overlay with opacity transition

## Permissions
- No restrictions — presentation component

## Telemetry
- `drawer.open` — Drawer opened (with placement, size)
- `drawer.close` — Drawer closed

## React Query
- None — stateless container

## Dependencies
- `shared/hooks/useEscapeKey` — Keyboard dismiss
- `shared/hooks/useClickOutside` — Mask click
- `shared/hooks/useScrollLock` — Prevent background scroll

## Future Extensions
- Nested drawers with stack management
- Resize handle for adjustable width
- Drawer groups (multiple panels)
- Animation presets (slide, fade)
