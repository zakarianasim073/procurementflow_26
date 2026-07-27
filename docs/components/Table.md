# Table Component Contract

**Package**: `shared/ui`  
**Type**: Data Display Component  
**Stability**: Stable  

---

## Purpose

Sortable, filterable, paginated data table with column resizing, row selection, and virtualization. Base for BoqTable, RateAnalysisTable, and entity lists.

---

## Props

```typescript
interface TableProps<T> {
  /** Column definitions */
  columns: ColumnDef<T>[];
  /** Row data */
  data: T[];
  /** Row key accessor */
  getKey: (row: T) => string;
  /** Row click handler */
  onRowClick?: (row: T) => void;
  /** Selection */
  selectedKeys?: Set<string>;
  onSelectionChange?: (keys: Set<string>) => void;
  /** Sorting */
  sortBy?: string;
  sortOrder?: 'asc' | 'desc';
  onSortChange?: (key: string, order: 'asc' | 'desc') => void;
  /** Filtering */
  filters?: Record<string, unknown>;
  onFilterChange?: (filters: Record<string, unknown>) => void;
  /** Pagination */
  pagination?: {
    page: number;
    pageSize: number;
    total: number;
    onPageChange: (page: number) => void;
    onPageSizeChange: (size: number) => void;
  };
  /** Virtualization */
  virtualized?: boolean;
  rowHeight?: number;
  /** Loading */
  loading?: boolean;
  /** Empty state */
  emptyMessage?: string;
  /** Row expansion */
  expandedKeys?: Set<string>;
  onExpandedChange?: (keys: Set<string>) => void;
  renderExpanded?: (row: T) => React.ReactNode;
  /** Custom className */
  className?: string;
}

interface ColumnDef<T> {
  key: string;
  header: string;
  accessor: keyof T | ((row: T) => React.ReactNode);
  width?: number | string;
  minWidth?: number;
  maxWidth?: number;
  sortable?: boolean;
  filterable?: boolean;
  resizable?: boolean;
  align?: 'left' | 'center' | 'right';
  sticky?: 'left' | 'right';
  render?: (value: unknown, row: T) => React.ReactNode;
  headerRender?: () => React.ReactNode;
}
```

---

## Slots

| Slot | Required | Description |
|------|----------|-------------|
| `header` | No | Custom header (title, actions) |
| `footer` | No | Summary row, pagination |
| `empty` | No | Custom empty state |
| `loading` | No | Custom loading |

---

## State

| State | Trigger | Visual |
|-------|---------|--------|
| `loading` | `loading=true` | Row skeletons (5) |
| `empty` | `data.length === 0` | Empty state |
| `sorting` | Header click | Sort indicator |
| `filtering` | Filter input | Filter chips |
| `selecting` | Checkbox | Row highlight |
| `expanding` | Expand click | Detail row |
| `resizing` | Column drag | Resize handle |

---

## Accessibility

- **Role**: `table` with hidden `caption`
- **Headers**: `scope="col"`, `aria-sort`
- **Rows**: `role="row"`, `aria-selected`
- **Cells**: `role="gridcell"` or `role="columnheader"`
- **Pagination**: `nav` with `aria-label`
- **Keyboard**: Full grid navigation

---

## Keyboard

| Key | Action |
|-----|--------|
| `Tab` | Next cell |
| `Shift+Tab` | Previous cell |
| `Arrow Keys` | Navigate grid |
| `Enter` | Activate row / edit cell |
| `Space` | Toggle row selection |
| `Ctrl+A` | Select all |
| `Escape` | Clear selection |
| `Home/End` | First/Last cell |

---

## Mobile

- **< 1024px**: Horizontal scroll, sticky first 2-3 columns
- **Row Height**: 56px minimum
- **Actions**: Collapsed to kebab menu
- **Pagination**: Simplified (prev/next + page input)

---

## Permissions

| Role | View | Sort | Filter | Select | Export |
|------|------|------|--------|--------|--------|
| `viewer` | ✅ | ✅ | ✅ | ❌ | ❌ |
| `estimator` | ✅ | ✅ | ✅ | ✅ | ✅ |
| `admin` | ✅ | ✅ | ✅ | ✅ | ✅ |

---

## Telemetry

| Event | Properties |
|-------|------------|
| `table_sort` | `column`, `order` |
| `table_filter` | `column`, `value` |
| `table_page_change` | `page`, `page_size` |
| `table_row_click` | `row_key` |
| `table_selection_change` | `count` |
| `table_export` | `format`, `row_count` |

---

## React Query Integration

```typescript
const { data } = useQuery({
  queryKey: ['tenders', { page, pageSize, filters, sortBy, sortOrder }],
  queryFn: () => fetchTenders({ page, pageSize, filters, sortBy, sortOrder })
});

<Table
  columns={tenderColumns}
  data={data?.items || []}
  getKey={t => t.id}
  onRowClick={t => navigate(`/tender/${t.id}`)}
  pagination={{
    page: data?.page || 1,
    pageSize: data?.pageSize || 25,
    total: data?.total || 0,
    onPageChange: setPage,
    onPageSizeChange: setPageSize
  }}
  sortBy={sortBy}
  sortOrder={sortOrder}
  onSortChange={(key, order) => { setSortBy(key); setSortOrder(order); }}
  filters={filters}
  onFilterChange={setFilters}
  selectedKeys={selectedIds}
  onSelectionChange={setSelectedIds}
  virtualized
  rowHeight={52}
/>
```

---

## Column Types

| Type | Render | Sortable | Filterable |
|------|--------|----------|------------|
| `text` | String | ✅ | Text |
| `number` | Formatted | ✅ | Range |
| `currency` | Formatted | ✅ | Range |
| `percentage` | Formatted | ✅ | Range |
| `date` | Formatted | ✅ | Date range |
| `boolean` | Checkbox/Icon | ✅ | Yes/No |
| `badge` | Badge | ✅ | Select |
| `action` | Buttons | ❌ | ❌ |

---

## Future Extensions

- [ ] Column reordering (drag-drop)
- [ ] Column visibility toggle
- [ ] Saved views/presets
- [ ] Inline editing
- [ ] Row drag-drop reordering
- [ ] Tree table (hierarchical)
- [ ] Pivot table mode
- [ ] Export to PNG/SVG