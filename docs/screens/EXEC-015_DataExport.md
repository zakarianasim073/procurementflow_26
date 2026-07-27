# EXEC-015: Data Export Screen Specification

**Module:** `features/data-export/DataExportPage`
**Layer:** features
**Version:** 1.0.0
**Status:** Draft
**Workspace:** Dashboard

## Purpose
Export data, reports, and analytics to various formats.

## Screen Layout

```
┌─────────────────────────────────────────────────────────────┐
│ ExecutiveHeader                                             │
├──────────┬──────────────────────────────────────────────────┤
│          │ Breadcrumb: Dashboard > Data Export               │
│ Workspace├──────────────────────────────────────────────────┤
│   Nav    │ DataExportHeader (exports, scheduled)            │
│          ├──────────────────────────────────────────────────┤
│          │ DataExport (main content)                        │
│          │ ┌────────────────────────────────────────────┐   │
│          │ │ ExportOptions (export types)                │   │
│          │ │ ┌──────┬──────┬──────┬──────┐              │   │
│          │ │ │Tenders│BOQ  │SOR   │Custom│              │   │
│          │ │ │      │     │      │Report│              │   │
│          │ │ └──────┴──────┴──────┴──────┘              │   │
│          │ ├────────────────────────────────────────────┤   │
│          │ │ ExportConfig (configuration)                │   │
│          │ ├────────────────────────────────────────────┤   │
│          │ │ ExportHistory (past exports)                │   │
│          │ └────────────────────────────────────────────┘   │
├──────────┴──────────────────────────────────────────────────┤
│ AiDock (export suggestions)                                 │
└─────────────────────────────────────────────────────────────┘
```

## Component Tree

```
DataExportPage
├── ExecutiveHeader
├── Breadcrumb
├── DataExportHeader
│   ├── KpiStrip (export_count, scheduled_count)
│   └── Button (New Export)
├── DataExport
│   ├── ExportOptions
│   │   └── ExportTypeCard × N
│   │       ├── icon
│   │       ├── name
│   │       ├── description
│   │       └── Button (Select)
│   ├── ExportConfig
│   │   ├── format_selector
│   │   ├── filter_options
│   │   ├── schedule_options
│   │   └── Button (Export Now)
│   ├── ExportHistory
│   │   └── ExportCard × N
│   │       ├── type
│   │       ├── format
│   │       ├── status
│   │       ├── timestamp
│   │       └── Button (Download)
│   └── ScheduledExports
│       └── ScheduleCard × N
│           ├── type
│           ├── frequency
│           ├── next_run
│           └── Button (Edit)
└── AiDock
    ├── AgentCard (Export Agent)
    └── EvidencePanel (export suggestions)
```

## Data Sources

### Export Options
```typescript
// API: GET /api/v1/reports/export/options
interface ExportOption {
  type: string;
  name: string;
  description: string;
  formats: string[];
  filters: FilterOption[];
}

interface FilterOption {
  name: string;
  type: string;
  options?: string[];
}
```

### Export History
```typescript
// API: GET /api/v1/reports/export/history
interface ExportHistory {
  exports: ExportEntry[];
  total_count: number;
}

interface ExportEntry {
  export_id: string;
  type: string;
  format: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  timestamp: string;
  file_url?: string;
  file_size?: number;
}
```

### React Query
```typescript
const { data: options } = useQuery({
  queryKey: ['reports', 'export', 'options'],
  queryFn: () => api.get('/api/v1/reports/export/options'),
});

const { data: history } = useQuery({
  queryKey: ['reports', 'export', 'history'],
  queryFn: () => api.get('/api/v1/reports/export/history'),
});

const createExport = useMutation({
  mutationFn: (request: ExportRequest) => api.post('/api/v1/reports/export', request),
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ['reports', 'export', 'history'] });
    toast.success('Export started');
  },
});
```

## Zustand Store
```typescript
// stores/dataExportStore.ts
interface DataExportState {
  selectedType: string | null;
  selectedFormat: string;
  filters: Record<string, any>;
  schedule: ScheduleConfig | null;
  setType: (type: string | null) => void;
  setFormat: (format: string) => void;
  setFilters: (filters: Record<string, any>) => void;
  setSchedule: (schedule: ScheduleConfig | null) => void;
}

interface ScheduleConfig {
  frequency: 'daily' | 'weekly' | 'monthly';
  time: string;
  recipients: string[];
}
```

## Interactions

### Select Export Type
1. Click export type card
2. Load configuration
3. Set filters
4. Choose format

### Export Now
1. Click Export Now button
2. Start export
3. Show progress
4. Provide download

### Schedule Export
1. Click Schedule button
2. Set frequency
3. Add recipients
4. Save schedule

### Download Export
1. Click Download button
2. Get file URL
3. Download file
4. Open file

## Responsive Breakpoints

| Breakpoint | Layout |
|------------|--------|
| Desktop (>1024px) | Full options + config |
| Tablet (768-1024px) | Stacked layout |
| Mobile (<768px) | Simplified options |

## Loading States
- Options: Skeleton cards
- Export: Progress indicator
- Download: Loading spinner

## Error States
- Export failure: Retry button
- Download failure: Toast error
- Network error: Toast notification

## Accessibility
- Options are focusable
- Progress announced via `aria-live`
- Screen reader: "Export processing, 50% complete"
- Keyboard: Tab through options

## Telemetry
- `data_export.view` — Screen loaded
- `data_export.select_type` — Type selected
- `data_export.export_now` — Export started
- `data_export.schedule` — Export scheduled
- `data_export.download` — File downloaded

## Implementation Notes
- Multiple export formats (CSV, Excel, PDF)
- Scheduled exports
- Export history
- AiDock provides export suggestions
- Large file handling
