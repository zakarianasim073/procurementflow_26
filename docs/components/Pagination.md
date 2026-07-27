# Pagination Component Contract

**Package**: `shared/ui`  
**Type**: Navigation Component  
**Stability**: Stable  

---

## Purpose

Page navigation for lists, tables, and search results. Supports multiple display modes, page size selection, and keyboard navigation.

---

## Props

```typescript
interface PaginationProps {
  /** Current page (1-indexed) */
  page: number;
  /** Total items */
  total: number;
  /** Items per page */
  pageSize: number;
  /** Page size options */
  pageSizeOptions?: number[]; // default: [10, 25, 50, 100]
  /** Change handlers */
  onPageChange: (page: number) => void;
  onPageSizeChange?: (size: number) => void;
  /** Display mode */
  variant?: 'full' | 'compact' | 'simple' | 'input';
  /** Show total count */
  showTotal?: boolean;
  /** Show page size selector */
  showSizeChanger?: boolean;
  /** Show first/last buttons */
  showFirstLast?: boolean;
  /** Custom className */
  className?: string;
}
```

---

## Variants

| Variant | Elements | Use Case |
|---------|----------|----------|
| `full` | Prev, Pages, Next, Size, Total | Tables, lists |
| `compact` | Prev, Page Input, Next | Toolbars |
| `simple` | Prev, Next only | Modals, cards |
| `input` | Page input + total | Direct navigation |

---

## Slots

| Slot | Required | Description |
|------|----------|-------------|
| `prev` | No | Custom prev button |
| `next` | No | Custom next button |
| `page` | No | Custom page button |
| `sizeSelect` | No | Custom size selector |

---

## State

| State | Trigger | Visual |
|-------|---------|--------|
| `default` | Initial | Normal |
| `first` | Page 1 | Prev disabled |
| `last` | Last page | Next disabled |
| `loading` | Transition | Spinner in buttons |
| `disabled` | `total=0` | All disabled |

---

## Accessibility

- **Role**: `navigation` with `aria-label="Pagination"`
- **Buttons**: `aria-label="Page X"`, `aria-current="page"`
- **First/Last**: `aria-label="First page"`, `aria-label="Last page"`
- **Keyboard**: Full navigation

---

## Keyboard

| Key | Action |
|-----|--------|
| `Arrow Left` | Previous page |
| `Arrow Right` | Next page |
| `Home` | First page |
| `End` | Last page |
| `Enter` | Activate page |

---

## Loading

- **Transition**: Spinner in prev/next during page change
- **Debounce**: 300ms between rapid clicks

---

## Mobile

- **< 640px**: Show prev/next + page input only
- **Touch**: 44×44mm targets
- **Ellipsis**: Hide intermediate pages

---

## Permissions

Not applicable

---

## Telemetry

| Event | Properties |
|-------|------------|
| `pagination_change` | `page`, `page_size`, `total` |
| `page_size_change` | `new_size` |

---

## React Query

```typescript
const { data } = useQuery({
  queryKey: ['items', { page, pageSize, filters }],
  queryFn: () => fetchItems({ page, pageSize, filters })
});

<Pagination
  page={page}
  total={data?.total || 0}
  pageSize={pageSize}
  onPageChange={setPage}
  onPageSizeChange={setPageSize}
/>
```

---

## Dependencies

- `Select` (page size)
- `Input` (page input)
- `Button` (navigation)
- `lucide-react`: `ChevronLeft`, `ChevronRight`, `ChevronFirst`, `ChevronLast`, `MoreHorizontal`

---

## Usage Examples

```tsx
// Full
<Pagination
  page={page}
  total={total}
  pageSize={pageSize}
  onPageChange={setPage}
  onPageSizeChange={setPageSize}
  pageSizeOptions={[10, 25, 50, 100]}
  showTotal
  showSizeChanger
/>

// Compact for toolbar
<Pagination
  page={page}
  total={total}
  pageSize={pageSize}
  onPageChange={setPage}
  variant="compact"
/>

// Simple for cards
<Pagination
  page={page}
  total={total}
  pageSize={pageSize}
  onPageChange={setPage}
  variant="simple"
/>
```

---

## Layout

```
Full:
[◀ First] [◀ Prev] [1] [2] [3] ... [10] [Next ▶] [Last ▶]  [Page Size ▼]  [Showing 1-25 of 1,247]

Compact:
[◀]  [1 / 42]  [▶]

Simple:
[◀ Previous] [Next ▶]
```

---

## Future Extensions

- [ ] Jump to page input
- [ ] Page size presets
- [ ] Infinite scroll toggle
- [ ] URL sync (hash/history)
- [ ] RTL support