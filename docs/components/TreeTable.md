# TreeTable Component Contract

**Module:** `shared/ui/TreeTable`
**Layer:** shared
**Version:** 1.0.0
**Status:** Draft

## Purpose
Hierarchical data grid with expandable/collapsible rows for displaying nested structures like organizational hierarchies, folder structures, and multi-level BOQ items.

## Props
```typescript
interface TreeTableProps<T extends Record<string, any>> {
  data: TreeNode<T>[];
  columns: Column<T>[];
  rowKey: keyof T;
  childrenKey?: string;
  defaultExpandAll?: boolean;
  defaultExpandedKeys?: string[];
  onExpand?: (expandedKeys: string[], node: T) => void;
  onRowClick?: (node: T) => void;
  onRowSelect?: (selectedKeys: string[]) => void;
  selectable?: boolean;
  multiSelect?: boolean;
  indentSize?: number;
  showIcon?: boolean;
  expandIcon?: ReactNode;
  collapseIcon?: ReactNode;
  loading?: boolean;
  emptyText?: string;
  className?: string;
  testId?: string;
}

interface TreeNode<T> {
  data: T;
  children?: TreeNode<T>[];
  isLeaf?: boolean;
}

interface Column<T> {
  key: string;
  title: string;
  width?: number;
  align?: 'left' | 'center' | 'right';
  render?: (value: any, node: T, level: number) => ReactNode;
  sortable?: boolean;
}
```

## Slots
- `expandIcon` — Custom expand indicator
- `collapseIcon` — Custom collapse indicator
- `empty` — Empty state content
- `rowExpand` — Expanded row content

## State
```typescript
interface TreeTableState {
  expandedKeys: Set<string>;
  selectedKeys: Set<string>;
  sortConfig: { key: string; direction: 'asc' | 'desc' } | null;
}
```

## Accessibility
- **ARIA:** `role="treegrid"`, `aria-expanded`, `aria-level`, `aria-setsize`
- **Keyboard:** Arrow keys navigate, Space/Enter expand/collapse, Shift+Click for range select
- **Focus:** Visible focus ring on active cell, roving tabindex

## Loading
- Skeleton rows with matching indent levels
- Progressive expansion with loading indicator per node

## Errors
- Empty state with illustration when no data
- Error boundary for render failures

## Keyboard
| Key | Action |
|-----|--------|
| ArrowDown | Next row |
| ArrowUp | Previous row |
| ArrowRight | Expand or move to child |
| ArrowLeft | Collapse or move to parent |
| Space | Toggle selection |
| Enter | Expand/collapse |
| Home | First row |
| End | Last visible row |

## Mobile
- Horizontal scroll with sticky first column
- Reduced indent (12px) on small screens
- Touch-friendly expand/collapse targets (min 44px)

## Permissions
- No restrictions — read-only display component

## Telemetry
- `tree_table.row_expand` — Node expanded
- `tree_table.row_collapse` — Node collapsed
- `tree_table.row_select` — Node selected
- `tree_table.sort` — Column sorted

## React Query
- Component is presentation-only; data comes from parent
- Parent manages query state and passes flat/hierarchical data

## Dependencies
- `shared/ui/Badge` — For status indicators
- `shared/ui/Checkbox` — For row selection
- `shared/ui/Skeleton` — Loading state

## Future Extensions
- Drag-and-drop row reordering
- Inline editing
- Copy/paste support
- Export to Excel with hierarchy preserved
