# ENT-009: Import/Export Screen Specification

**Module:** `features/import-export/ImportExportPage`
**Layer:** features
**Version:** 1.0.0
**Status:** Draft
**Workspace:** Settings

## Purpose
Data import/export, bulk operations, and data synchronization management.

## Screen Layout

```
┌─────────────────────────────────────────────────────────────┐
│ ExecutiveHeader                                             │
├──────────┬──────────────────────────────────────────────────┤
│          │ Breadcrumb: Settings > Import/Export              │
│ Workspace├──────────────────────────────────────────────────┤
│   Nav    │ ImportExportHeader (status, history)             │
│          ├──────────────────────────────────────────────────┤
│          │ ImportExport (main content)                      │
│          │ ┌────────────────────────────────────────────┐   │
│          │ │ Tabs: [Import] [Export] [History] [Sync]   │   │
│          │ ├────────────────────────────────────────────┤   │
│          │ │ ImportWizard (upload + map + validate)      │   │
│          │ │ ExportWizard (select + configure + download)│   │
│          │ │ HistoryLog (past operations)                │   │
│          │ │ SyncManager (data synchronization)          │   │
│          │ └────────────────────────────────────────────┘   │
├──────────┴──────────────────────────────────────────────────┤
│ AiDock (import suggestions, data insights)                  │
└─────────────────────────────────────────────────────────────┘
```

## Component Tree

```
ImportExportPage
├── ExecutiveHeader
├── Breadcrumb
├── ImportExportHeader
│   ├── KpiStrip (imports, exports, last_sync)
│   └── Badge (active_operations)
├── ImportExport
│   ├── Tabs
│   │   ├── ImportTab
│   │   │   └── ImportWizard
│   │   │       ├── Step1_Upload
│   │   │       │   └── FileUpload
│   │   │       ├── Step2_Map
│   │   │       │   └── ColumnMapper
│   │   │       ├── Step3_Validate
│   │   │       │   └── ValidationResults
│   │   │       └── Step4_Import
│   │   │           └── ImportProgress
│   │   ├── ExportTab
│   │   │   └── ExportWizard
│   │   │       ├── Step1_Select
│   │   │       │   └── DataTypeSelector
│   │   │       ├── Step2_Configure
│   │   │       │   └── ExportConfig
│   │   │       └── Step3_Download
│   │   │           └── ExportProgress
│   │   ├── HistoryTab
│   │   │   └── HistoryLog
│   │   │       └── Table<Operation>
│   │   │           ├── type (import/export)
│   │   │           ├── status
│   │   │           ├── started_at
│   │   │           └── records
│   │   └── SyncTab
│   │       └── SyncManager
│   │           ├── SyncStatus
│   │           ├── SyncHistory
│   │           └── Button (Sync Now)
│   └── OperationDetail
│       ├── progress
│       ├── results
│       └── errors
└── AiDock
    ├── AgentCard (Data Agent)
    └── EvidencePanel (import/export insights)
```

## Data Sources

### Import Operations
```typescript
// API: POST /api/v1/import
interface ImportRequest {
  file: File;
  data_type: string;
  mapping?: Record<string, string>;
  options?: Record<string, any>;
}

interface ImportResponse {
  operation_id: string;
  status: 'uploading' | 'validating' | 'importing' | 'completed' | 'failed';
  progress: number;
  total_records: number;
  processed_records: number;
  errors: ImportError[];
}

interface ImportError {
  row: number;
  field: string;
  message: string;
  value: string;
}
```

### Export Operations
```typescript
// API: POST /api/v1/export
interface ExportRequest {
  data_type: string;
  filters?: Record<string, any>;
  format: 'csv' | 'excel' | 'json';
  options?: Record<string, any>;
}

interface ExportResponse {
  operation_id: string;
  status: 'processing' | 'completed' | 'failed';
  progress: number;
  download_url?: string;
  total_records: number;
}
```

### React Query
```typescript
const startImport = useMutation({
  mutationFn: (request: ImportRequest) => {
    const formData = new FormData();
    formData.append('file', request.file);
    formData.append('data_type', request.data_type);
    return api.post('/api/v1/import', formData);
  },
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ['import-export', 'history'] });
    toast.success('Import started');
  },
});

const startExport = useMutation({
  mutationFn: (request: ExportRequest) => api.post('/api/v1/export', request),
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ['import-export', 'history'] });
    toast.success('Export started');
  },
});

const { data: history } = useQuery({
  queryKey: ['import-export', 'history'],
  queryFn: () => api.get('/api/v1/import-export/history'),
});
```

## Zustand Store
```typescript
// stores/importExportStore.ts
interface ImportExportState {
  activeTab: string;
  currentOperation: string | null;
  setTab: (tab: string) => void;
  setOperation: (id: string | null) => void;
}
```

## Interactions

### Import Data
1. Click Import tab
2. Upload file
3. Map columns
4. Validate data
5. Start import
6. Monitor progress

### Export Data
1. Click Export tab
2. Select data type
3. Configure options
4. Start export
5. Download file

### View History
1. Click History tab
2. View past operations
3. Click operation for details
4. Download results

### Sync Data
1. Click Sync tab
2. View sync status
3. Click "Sync Now"
4. Monitor progress

## Responsive Breakpoints

| Breakpoint | Layout |
|------------|--------|
| Desktop (>1024px) | Full tabs with wizards |
| Tablet (768-1024px) | Stacked tabs |
| Mobile (<768px) | Single tab view |

## Loading States
- Upload: Progress bar
- Import: Progress indicator
- Export: Progress indicator
- History: Skeleton table

## Error States
- Upload failure: Retry button
- Validation errors: Error list
- Import failure: Error details
- Network error: Toast notification

## Accessibility
- Wizard steps are focusable
- Progress announced via `aria-live`
- Screen reader: "Importing X of Y records"
- Keyboard: Tab through steps, Enter to proceed

## Telemetry
- `import_export.view` — Screen loaded
- `import_export.import_start` — Import started
- `import_export.export_start` — Export started
- `import_export.sync` — Sync triggered

## Implementation Notes
- Step-by-step wizards for import/export
- Real-time progress monitoring
- Validation before import
- History for audit trail
- AiDock provides data insights
