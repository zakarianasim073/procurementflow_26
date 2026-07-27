# TreeSelect Component Contract

**Package**: `shared/ui`  
**Type**: Form Input Component  
**Stability**: Stable  

---

## Purpose

Hierarchical tree selector for nested data like department trees, ministry hierarchies, and category structures. Supports single/multi-select with search and keyboard navigation.

---

## Props

```typescript
interface TreeSelectProps<T = string> {
  /** Selected value(s) */
  value: T | T[] | null;
  /** Change handler */
  onChange: (value: T | T[] | null) => void;
  /** Tree data */
  tree: TreeNode<T>[];
  /** Multiple selection */
  multiple?: boolean;
  /** Placeholder */
  placeholder?: string;
  /** Searchable */
  searchable?: boolean;
  /** Show checkboxes (multiple mode) */
  checkboxes?: boolean; // default: true when multiple
  /** Show icons */
  showIcons?: boolean;
  /** Show path (e.g., "Ministry > Division > Office") */
  showPath?: boolean;
  /** Disabled */
  disabled?: boolean;
  /** Error message */
  error?: string;
  /** Label */
  label?: string;
  /** Helper text */
  helperText?: string;
  /** Custom className */
  className?: string;
}

interface TreeNode<T> {
  value: T;
  label: string;
  children?: TreeNode<T>[];
  icon?: React.ReactNode;
  disabled?: boolean;
  badge?: string | number;
  metadata?: Record<string, any>;
}
```

---

## Slots

| Slot | Required | Description |
|------|----------|-------------|
| `trigger` | No | Custom trigger rendering |
| `node` | No | Custom tree node |
| `empty` | No | Empty search state |

---

## State

| State | Trigger | Visual |
|-------|---------|--------|
| `closed` | Default | Trigger only |
| `open` | Click trigger | Tree panel |
| `searching` | Typing | Filtered tree |
| `expanded` | Node expand | Children visible |
| `loading` | Async tree | Skeleton |

---

## Accessibility

- **Role**: `tree` with `treeitem`, `group`
- **ARIA**: `aria-expanded`, `aria-selected`, `aria-level`
- **Keyboard**: Full tree navigation pattern
- **Screen Reader**: Announces hierarchy levels

---

## Keyboard

| Key | Action |
|-----|--------|
| `Tab` | Focus trigger / tree |
| `Arrow Down` | Next visible node |
| `Arrow Up` | Previous visible node |
| `Arrow Right` | Expand node / Next child |
| `Arrow Left` | Collapse node / Parent |
| `Home` | First node |
| `End` | Last visible node |
| `Enter` / `Space` | Select / Toggle expand |
| `*` | Expand all siblings |
| `Type` | Search (when focused) |

---

## Usage Examples

```tsx
// Single select — department tree
<TreeSelect
  value={selectedDepartment}
  onChange={setSelectedDepartment}
  tree={departmentTree}
  searchable
  showPath
  placeholder="Select department"
/>

// Multi-select with checkboxes
<TreeSelect
  multiple
  checkboxes
  value={selectedDepartments}
  onChange={setSelectedDepartments}
  tree={departmentTree}
  searchable
  placeholder="Select departments"
/>

// Ministry hierarchy (e-GP)
<TreeSelect
  value={selectedMinistry}
  onChange={setSelectedMinistry}
  tree={ministryTree.map(m => ({
    value: m.id,
    label: m.name,
    children: m.offices.map(o => ({
      value: o.id,
      label: o.name,
      badge: o.total_packages
    }))
  }))}
  searchable
  showIcons
  placeholder="Select ministry/office"
/>

// Category hierarchy
<TreeSelect
  multiple
  value={selectedCategories}
  onChange={setSelectedCategories}
  tree={categoryTree}
  checkboxes
  showPath
  placeholder="Select categories"
/>
```

---

## Tree Data Pattern

```typescript
const ministryTree: TreeNode[] = [
  {
    value: 'ministry-1',
    label: 'Ministry of Road Transport',
    icon: <Building2 />,
    children: [
      {
        value: 'office-1',
        label: 'BWDB Dhaka Division',
        icon: <Building />,
        badge: 45,
        children: [
          { value: 'dept-1', label: 'Bridge Construction', badge: 12 },
          { value: 'dept-2', label: 'Drainage', badge: 8 }
        ]
      },
      { value: 'office-2', label: 'BWDB Chattogram', badge: 38 }
    ]
  },
  {
    value: 'ministry-2',
    label: 'Ministry of Water Resources',
    icon: <Building2 />,
    children: [...]
  }
];
```

---

## Future Extensions
- [ ] Async tree loading (lazy children)
- [ ] Drag-drop reorder
- [ ] Custom node actions
- [ ] Virtualized for large trees (1000+ nodes)
- [ ] Keyboard shortcut hints