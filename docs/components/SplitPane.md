# SplitPane Component Contract

**Module:** `shared/ui/SplitPane`
**Layer:** shared
**Version:** 1.0.0
**Status:** Draft

## Purpose
Resizable split panel layout for side-by-side views (BOQ comparison, tender vs. SOR rates, document preview + metadata).

## Props
```typescript
interface SplitPaneProps {
  children: [ReactNode, ReactNode];
  direction?: 'horizontal' | 'vertical';
  defaultSplit?: number;
  minSplit?: number;
  maxSplit?: number;
  split?: number;
  onSplitChange?: (split: number) => void;
  resizable?: boolean;
  collapsible?: boolean;
  collapseThreshold?: number;
  onCollapse?: (pane: 'first' | 'second') => void;
  className?: string;
  testId?: string;
}

interface SplitPaneDividerProps {
  direction: 'horizontal' | 'vertical';
  onDragStart?: () => void;
  onDragEnd?: () => void;
  disabled?: boolean;
}
```

## Slots
- `first` — Left/top pane
- `second` — Right/bottom pane
- `divider` — Custom divider handle
- `collapseLeft` — Collapse left button
- `collapseRight` — Collapse right button

## State
```typescript
interface SplitPaneState {
  split: number;
  isDragging: boolean;
  isCollapsed: 'first' | 'second' | null;
}
```

## Accessibility
- **ARIA:** `role="separator"`, `aria-valuenow`, `aria-valuemin`, `aria-valuemax`
- **Keyboard:** Arrow keys adjust split (1px/10px), Enter resets to default
- **Focus:** Visible focus ring on divider

## Loading
- N/A — layout component

## Errors
- N/A — layout component

## Keyboard
| Key | Action |
|-----|--------|
| ArrowLeft/Up | Decrease split (1px) |
| ArrowRight/Down | Increase split (1px) |
| Shift+Arrow | Adjust split (10px) |
| Enter | Reset to default split |
| Home | Collapse to minimum |
| End | Expand to maximum |

## Mobile
- Stacked vertically below 768px
- Tab toggle between panes instead of split
- Swipe to switch panes

## Permissions
- No restrictions — layout component

## Telemetry
- `split_pane.resize` — Split changed (from, to)
- `split_pane.collapse` — Pane collapsed
- `split_pane.expand` — Pane expanded

## React Query
- None — stateless layout

## Dependencies
- `shared/hooks/useDrag` — Drag handling
- `shared/hooks/useMediaQuery` — Responsive breakpoint

## Future Extensions
- Multi-pane splits (nested SplitPanes)
- Snap-to-grid positions
- Save/restore layout preferences
- Animated transitions on collapse/expand
