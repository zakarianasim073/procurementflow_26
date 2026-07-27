# ContextMenu Component Contract

**Module:** `shared/ui/ContextMenu`
**Layer:** shared
**Version:** 1.0.0
**Status:** Draft

## Purpose
Right-click or long-press menu for contextual actions on tender items, BOQ rows, contractor entries, and other data elements.

## Props
```typescript
interface ContextMenuProps {
  trigger: ReactNode;
  items: ContextMenuItem[];
  onAction: (action: string, data?: any) => void;
  data?: any;
  placement?: 'bottom-start' | 'bottom-end' | 'top-start' | 'top-end';
  className?: string;
  testId?: string;
}

interface ContextMenuItem {
  key: string;
  label: string;
  icon?: ReactNode;
  shortcut?: string;
  disabled?: boolean;
  danger?: boolean;
  divider?: boolean;
  children?: ContextMenuItem[];
}
```

## Slots
- `trigger` — Element that opens menu on right-click
- `item` — Custom item renderer
- `icon` — Custom icon slot per item
- `submenu` — Nested menu container

## State
```typescript
interface ContextMenuState {
  isOpen: boolean;
  position: { x: number; y: number };
  activeItem: string | null;
  submenuOpen: string | null;
}
```

## Accessibility
- **ARIA:** `role="menu"`, `role="menuitem"`, `aria-haspopup="true"` for submenus
- **Keyboard:** Arrow keys navigate, Enter activates, Escape closes, submenu on ArrowRight
- **Focus:** Focus trap within menu, auto-focus first item

## Loading
- N/A — instant display

## Errors
- N/A — menu items are static

## Keyboard
| Key | Action |
|-----|--------|
| ArrowDown | Next item |
| ArrowUp | Previous item |
| ArrowRight | Open submenu |
| ArrowLeft | Close submenu / parent menu |
| Enter | Activate item |
| Escape | Close menu |
| Home | First item |
| End | Last item |

## Mobile
- Long-press (500ms) triggers menu
- Full-width bottom sheet on mobile
- Larger touch targets (min 44px)

## Permissions
- Items filtered by user permissions
- Disabled items for unauthorized actions

## Telemetry
- `context_menu.open` — Menu opened (trigger element)
- `context_menu.action` — Item selected (action key)

## React Query
- None — pure UI component

## Dependencies
- Floating UI for positioning
- `shared/hooks/useClickOutside` for dismissal
- `shared/hooks/useLongPress` for mobile

## Future Extensions
- Drag-and-drop reorder within menu
- Keyboard shortcut recording
- Custom menu theming per workspace
- Animated submenu transitions
