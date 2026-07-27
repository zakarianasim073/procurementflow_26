# DataGrid Component Contract

**Package**: `widgets/data`  
**Type**: Data Display Component  
**Stability**: Stable  

---

## Purpose

Advanced data grid with inline editing, column management, export, and virtualization. Enterprise-grade table for large datasets (10k+ rows).

---

## Props

```typescript
interface DataGridProps<T> {
  /** Column definitions */
  columns: DataGridColumn<T>[];
  /** Row data */
  data: T[];
  /** Row key accessor */
  getRowId: (row: T) => string;
  
  // Selection
  selectedRows?: Set<string>;
  onSelectionChange?: (rows: Set<string>) => void;
  
  // Editing
  editable?: boolean;
  onCellEdit?: (rowId: string, columnId: string, value: any) => Promise<boolean>;
  onRowAdd?: () => Promise<T | null>;
  onRowDelete?: (rowId: string) => Promise<boolean>;
  
  // Sorting
  sortModel?: SortModel;
  onSortModelChange?: (model: SortModel) => void;
  
  // Filtering
  filterModel?: FilterModel;
  onFilterModelChange?: (model: FilterModel) => void;
  
  // Pagination
  pagination?: {
    page: number;
    pageSize: number;
    total: number;
    onPageChange: (page: number) => void;
    onPageSizeChange: (size: number) => void;
    pageSizeOptions?: number[];
  };
  
  // Virtualization
  virtualized?: boolean;
  rowHeight?: number;
  
  // UI
  loading?: boolean;
  error?: string;
  hideHeader?: boolean;
  hideFooter?: boolean;
  showRowNumbers?: boolean;
  rowHoverHighlight?: boolean;
  
  // Customization
  components?: {
    Toolbar?: React.ComponentType;
    Pagination?: React.ComponentType;
    LoadingOverlay?: React.ComponentType;
    NoRowsOverlay?: React.ComponentType;
    Cell?: React.ComponentType<CellProps<T>>;
    HeaderCell?: React.ComponentType<HeaderCellProps<T>>;
    Row?: React.ComponentType<RowProps<T>>;
  };
  
  // Events
  onRowClick?: (row: T, event: React.MouseEvent) => void;
  onRowDoubleClick?: (row: T, event: React.MouseEvent) => void;
  onCellClick?: (row: T, column: DataGridColumn<T>, event: React.MouseEvent) => void;
  onContextMenu?: (row: T, event: React.MouseEvent) => void;
  
  // Export
  exportOptions?: {
    formats?: ('csv' | 'xlsx' | 'pdf')[];
    filename?: string;
    excludeColumns?: string[];
  };
  
  className?: string;
}

interface DataGridColumn<T> {
  field: string;
  headerName: string;
  description?: string;
  width?: number | string;
  minWidth?: number;
  maxWidth?: number;
  flex?: number;
  editable?: boolean;
  sortable?: boolean;
  filterable?: boolean;
  resizable?: boolean;
  hideable?: boolean;
  pinned?: 'left' | 'right';
  align?: 'left' | 'center' | 'right';
  headerAlign?: 'left' | 'center' | 'right';
  type?: 'string' | 'number' | 'currency' | 'percentage' | 'date' | 'datetime' | 'boolean' | 'badge' | 'action' | 'custom';
  valueGetter?: (row: T) => any;
  valueSetter?: (row: T, value: any) => T;
  valueFormatter?: (value: any, row: T) => React.ReactNode;
  renderCell?: (value: any, row: T) => React.ReactNode;
  renderHeader?: () => React.ReactNode;
  filterOperators?: FilterOperator[];
  editorComponent?: React.ComponentType<EditorProps<T>>;
  validation?: (value: any, row: T) => string | null;
}

interface SortModel {
  field: string;
  sort: 'asc' | 'desc';
}

interface FilterModel {
  items: FilterItem[];
  logic?: 'AND' | 'OR';
}

interface FilterItem {
  field: string;
  operator: string;
  value: any;
}
```

---

## Slots

| Slot | Description |
|------|-------------|
| `toolbar` | Custom toolbar (search, export, actions) |
| `pagination` | Custom pagination |
| `loading` | Loading overlay |
| `noRows` | Empty state |
| `cell` | Custom cell rendering |
| `header` | Custom header |
| `row` | Custom row wrapper |

---

## State

| State | Visual |
|-------|--------|
| `loading` | Spinner overlay, disabled interactions |
| `editing` | Cell in edit mode, save/cancel buttons |
| `validating` | Spinner in cell, disabled |
| `error` | Red border, error tooltip |
| `selected` | Highlighted row, checkbox |
| `drag` | Drag preview, drop zones |

---

## Accessibility

- **Role**: `grid` with `row`/`gridcell`
- **ARIA**: `aria-sort`, `aria-selected`, `aria-expanded`
- **Keyboard**: Full grid navigation (arrows, tab, enter, escape)
- **Screen Reader**: Announces cell changes, sort, filter

---

## Keyboard

| Key | Action |
|-----|--------|
| `Arrow Keys` | Navigate cells |
| `Enter` | Edit cell / confirm |
| `Escape` | Cancel edit / exit |
| `Tab` | Next cell (edit mode) / next focusable |
| `Shift+Tab` | Previous cell |
| `Space` | Toggle selection |
| `Ctrl+A` | Select all |
| `Delete` | Delete row(s) |
| `F2` | Edit cell |
| `Ctrl+C` / `Ctrl+V` | Copy/Paste cells |

---

## Usage Examples

```tsx
// Basic data grid
<DataGrid
  columns={tenderColumns}
  data={tenders}
  getRowId={t => t.id}
  pagination={{
    page: page,
    pageSize: pageSize,
    total: total,
    onPageChange: setPage,
    onPageSizeChange: setPageSize
  }}
  sortModel={sortModel}
  onSortModelChange={setSortModel}
  filterModel={filterModel}
  onFilterModelChange={setFilterModel}
  onRowClick={(row) => navigate(`/tender/${row.id}`)}
/>

// Editable grid
<DataGrid
  columns={pricingColumns}
  data={pricingData}
  getRowId={p => p.id}
  editable
  onCellEdit={async (rowId, colId, value) => {
    const success = await updatePricing(rowId, colId, value);
    return success;
  }}
  onRowAdd={async () => {
    const newRow = await createPricingRow();
    return newRow;
  }}
  onRowDelete={async (id) => {
    return await deletePricingRow(id);
  }}
/>

// With virtualization (10k+ rows)
<DataGrid
  columns={largeDatasetColumns}
  data={largeDataset}
  getRowId={d => d.id}
  virtualized
  rowHeight={52}
  pagination={{
    page: 1,
    pageSize: 100,
    total: totalCount,
    onPageChange: setPage
  }}
/>

// With custom cell rendering
<DataGrid
  columns={[
    { field: 'name', headerName: 'Contractor', flex: 1 },
    { 
      field: 'status', 
      headerName: 'Status',
      width: 120,
      renderCell: (value) => <Badge variant={statusColor(value)}>{value}</Badge>
    },
    {
      field: 'actions',
      headerName: 'Actions',
      width: 100,
      renderCell: (_, row) => (
        <DropdownMenu
          items={[
            { label: 'View', onClick: () => view(row) },
            { label: 'Edit', onClick: () => edit(row) },
            { label: 'Delete', onClick: () => delete(row), danger: true }
          ]}
        />
      )
    }
  ]}
  data={contractorData}
  getRowId={c => c.id}
/>
```

---

## Column Types

| Type | Editor | Formatter | Filter |
|------|--------|-----------|--------|
| `string` | TextInput | Text | Contains/Equals |
| `number` | NumberInput | `toLocaleString()` | Range |
| `currency` | NumberInput | `formatCurrency()` | Range |
| `percentage` | NumberInput | `formatPercent()` | Range |
| `date` | DatePicker | `formatDate()` | DateRange |
| `datetime` | DateTimePicker | `formatDateTime()` | DateRange |
| `boolean` | Checkbox | Checkbox/Icon | Boolean |
| `badge` | Select | Badge | Multi-select |
| `action` | N/A | Custom | N/A |
| `custom` | Custom | Custom | Custom |

---

## Export

```tsx
<DataGrid
  // ...
  exportOptions={{
    formats: ['csv', 'xlsx', 'pdf'],
    filename: 'tender-data',
    excludeColumns: ['actions', 'internalId']
  }}
  components={{
    Toolbar: CustomToolbar
  }}
/>
```

---

## Performance

- **Virtualization**: Only renders visible rows (+ buffer)
- **Memoization**: `React.memo` on cells/rows
- **Batch Updates**: Batched state updates
- **Web Workers**: Heavy sorting/filtering (optional)

---

## Future Extensions

- [ ] Tree data (hierarchical)
- [ ] Pivot table mode
- [ ] Chart integration
- [ ] Collaborative editing
- [ ] Version history
- [ ] Column reordering (drag)
- [ ] Column groups
- [ ] Summary rows (totals, averages)