# DropdownMenu Component Contract

**Package**: `shared/ui`  
**Type**: Menu Component  
**Stability**: Stable  

---

## Purpose

Contextual dropdown menu for actions, navigation, and commands. Supports groups, dividers, keyboard navigation, and nested submenus.

---

## Props

```typescript
interface DropdownMenuProps {
  /** Trigger element */
  trigger: React.ReactElement;
  /** Menu items */
  items: MenuItem[];
  /** Alignment */
  align?: 'start' | 'end' | 'center';
  /** Offset */
  offset?: number; // default: 8
  /** Close on item click */
  closeOnClick?: boolean; // default: true
  /** Custom className */
  className?: string;
}

interface MenuItem {
  /** Unique ID */
  id: string;
  /** Label */
  label: string;
  /** Icon */
  icon?: React.ReactNode;
  /** Click handler */
  onClick?: () => void;
  /** Disabled */
  disabled?: boolean;
  /** Divider before */
  dividerBefore?: boolean;
  /** Divider after */
  dividerAfter?: boolean;
  /** Submenu */
  submenu?: MenuItem[];
  /** Shortcut */
  shortcut?: string;
  /** Danger action */
  danger?: boolean;
  /** Checked state */
  checked?: boolean;
  /** Custom render */
  render?: () => React.ReactNode;
}
```

---

## Slots

| Slot | Required | Description |
|------|----------|-------------|
| `trigger` | No | Custom trigger (default: children) |
| `item` | No | Custom item rendering |
| `divider` | No | Custom divider |
| `submenuTrigger` | No | Submenu indicator |

---

## State

| State | Trigger | Visual |
|-------|---------|--------|
| `closed` | Default | Hidden |
| `open` | Click trigger | Fade in + slide |
| `submenu-open` | Hover submenu | Side panel |
| `focus` | Keyboard | Ring on item |
| `disabled` | `disabled=true` | Muted, not focusable |

---

## Accessibility

- **Role**: `menu` with `role="menuitem"` items
- **ARIA**: `aria-haspopup`, `aria-expanded` on trigger
- **Keyboard**: Full menu navigation pattern
- **Submenu**: `aria-haspopup="menu"` on parent
- **Focus Trap**: Within open menu

---

## Keyboard

| Key | Action |
|-----|--------|
| `Enter` / `Space` | Open/Select |
| `Escape` | Close |
| `Arrow Down` | Next item |
| `Arrow Up` | Previous item |
| `Arrow Right` | Open submenu |
| `Arrow Left` | Close submenu / Parent |
| `Home` / `End` | First/Last item |
| `Tab` | Close menu |
| `Letter` | Type-to-select |

---

## Loading

Not applicable

---

## Errors

Not applicable

---

## Mobile

- **Touch**: Tap to open, tap item to select
- **Position**: Bottom sheet on < 640px
- **Swipe**: Swipe down to dismiss
- **Submenu**: Push animation

---

## Permissions

| Role | Can Access |
|------|------------|
| All authenticated | ✅ (items filtered by permission) |

---

## Telemetry

| Event | Properties |
|-------|------------|
| `dropdown_open` | `trigger_type` |
| `dropdown_item_click` | `item_id`, `has_submenu` |
| `dropdown_close` | `method` (click, escape, outside) |

---

## React Query

Not applicable

---

## Dependencies

- `Popper` (positioning)
- `FocusTrap` (keyboard)
- `Transition` (animations)
- `lucide-react`: `ChevronRight`, `Check`, `X`

---

## Usage Examples

```tsx
// Basic actions
<DropdownMenu
  trigger={<Button variant="ghost">Actions</Button>}
  items={[
    { id: 'edit', label: 'Edit', icon: <Edit />, onClick: handleEdit },
    { id: 'duplicate', label: 'Duplicate', icon: <Copy />, onClick: handleDuplicate },
    { dividerBefore: true },
    { id: 'delete', label: 'Delete', icon: <Trash2 />, onClick: handleDelete, danger: true }
  ]}
/>

// With submenu
<DropdownMenu
  trigger={<Button variant="outline">Export</Button>}
  items={[
    { id: 'excel', label: 'Excel (.xlsx)', icon: <FileSpreadsheet />, onClick: () => export('xlsx') },
    { id: 'pdf', label: 'PDF (.pdf)', icon: <FileText />, onClick: () => export('pdf') },
    { id: 'docx', label: 'Word (.docx)', icon: <FileDoc />, onClick: () => export('docx') },
    { dividerBefore: true },
    { id: 'all', label: 'All Formats', icon: <Download />, onClick: () => export('all') }
  ]}
/>

// With checked items
<DropdownMenu
  trigger={<Button variant="outline">View</Button>}
  items={[
    { id: 'show-completed', label: 'Show Completed', checked: showCompleted, onClick: toggleCompleted },
    { id: 'show-pending', label: 'Show Pending', checked: showPending, onClick: togglePending },
    { dividerBefore: true },
    { id: 'compact', label: 'Compact View', checked: compact, onClick: toggleCompact },
  ]}
/>

// Align end (for right-side triggers)
<DropdownMenu
  trigger={<Button variant="ghost">⋮</Button>}
  align="end"
  items={[...]}
/>

// With shortcuts
items={[
  { id: 'save', label: 'Save', shortcut: 'Ctrl+S', onClick: save },
  { id: 'save-as', label: 'Save As...', shortcut: 'Ctrl+Shift+S', onClick: saveAs },
]}
```

---

## Permissions (Item Filtering)

```tsx
const items = useMemo(() => [
  { id: 'edit', label: 'Edit', onClick: edit },
  ...(canDelete ? [{ id: 'delete', label: 'Delete', danger: true, onClick: delete }] : []),
  ...(isAdmin ? [{ id: 'admin', label: 'Admin Settings', onClick: admin }] : []),
], [canDelete, isAdmin]);
```

---

## Future Extensions

- [ ] Checkbox/radio groups
- [ ] Search/filter within menu
- [ ] Keyboard shortcuts display
- [ ] Menu sections with headers
- [ ] Infinite scroll for long menus
- [ ] Portal rendering to body