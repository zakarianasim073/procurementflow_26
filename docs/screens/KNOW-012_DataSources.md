# KNOW-012: Data Sources Screen Specification

**Module:** `features/data-sources/DataSourcesPage`
**Layer:** features
**Version:** 1.0.0
**Status:** Draft
**Workspace:** Knowledge

## Purpose
External data source management, API connections, and data synchronization.

## Screen Layout

```
┌─────────────────────────────────────────────────────────────┐
│ ExecutiveHeader                                             │
├──────────┬──────────────────────────────────────────────────┤
│          │ Breadcrumb: Knowledge > Data Sources              │
│ Workspace├──────────────────────────────────────────────────┤
│   Nav    │ DataSourcesHeader (count, status)                │
│          ├──────────────────────────────────────────────────┤
│          │ DataSources (main content)                       │
│          │ ┌────────────────────────────────────────────┐   │
│          │ │ Tabs: [Sources] [Sync] [Logs] [Settings]   │   │
│          │ ├────────────────────────────────────────────┤   │
│          │ │ SourceList (data source cards)               │   │
│          │ │ SyncManager (synchronization)                │   │
│          │ │ SyncLogs (sync history)                      │   │
│          │ │ SettingsForm (global config)                 │   │
│          │ └────────────────────────────────────────────┘   │
├──────────┴──────────────────────────────────────────────────┤
│ AiDock (data insights, synchronization)                     │
└─────────────────────────────────────────────────────────────┘
```

## Component Tree

```
DataSourcesPage
├── ExecutiveHeader
├── Breadcrumb
├── DataSourcesHeader
│   ├── KpiStrip (source_count, active_count, last_sync)
│   └── Button (Add Source)
├── DataSources
│   ├── Tabs
│   │   ├── SourcesTab
│   │   │   └── SourceList
│   │   │       └── SourceCard × N
│   │   │           ├── icon
│   │   │           ├── name
│   │   │           ├── type
│   │   │           ├── status
│   │   │           ├── last_sync
│   │   │           └── actions (edit, sync, delete)
│   │   ├── SyncTab
│   │   │   └── SyncManager
│   │   │       ├── SyncStatus
│   │   │       ├── SyncHistory
│   │   │       └── Button (Sync All)
│   │   ├── LogsTab
│   │   │   └── SyncLogs
│   │   │       └── Table<SyncLog>
│   │   │           ├── timestamp
│   │   │           ├── source
│   │   │           ├── status
│   │   │           ├── records
│   │   │           └── duration
│   │   └── SettingsTab
│   │       └── SettingsForm
│   │           ├── Input (sync_frequency)
│   │           ├── Switch (auto_sync)
│   │           ├── Input (timeout)
│   │           └── Button (Save)
│   └── SourceDetail
│       ├── configuration
│       ├── sync_status
│       └── data_preview
└── AiDock
    ├── AgentCard (Data Agent)
    └── EvidencePanel (data insights)
```

## Data Sources

### Data Sources
```typescript
// API: GET /api/v1/knowledge/data-sources
interface DataSourceList {
  sources: DataSource[];
  total_count: number;
}

interface DataSource {
  source_id: string;
  name: string;
  type: 'api' | 'database' | 'file' | 'webhook';
  status: 'active' | 'inactive' | 'error';
  last_sync?: string;
  sync_count: number;
  record_count: number;
  error_count: number;
  config: Record<string, any>;
}
```

### Sync Logs
```typescript
// API: GET /api/v1/knowledge/data-sources/logs
interface SyncLogList {
  logs: SyncLog[];
  total_count: number;
}

interface SyncLog {
  log_id: string;
  timestamp: string;
  source_id: string;
  source_name: string;
  status: 'success' | 'failed' | 'partial';
  records_synced: number;
  duration: number;
  error?: string;
}
```

### React Query
```typescript
const { data: sources } = useQuery({
  queryKey: ['knowledge', 'data-sources'],
  queryFn: () => api.get('/api/v1/knowledge/data-sources'),
});

const { data: logs } = useQuery({
  queryKey: ['knowledge', 'data-sources', 'logs', filters],
  queryFn: () => api.get('/api/v1/knowledge/data-sources/logs', { params: filters }),
});

const syncSource = useMutation({
  mutationFn: (sourceId: string) => api.post(`/api/v1/knowledge/data-sources/${sourceId}/sync`),
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ['knowledge', 'data-sources'] });
    toast.success('Sync started');
  },
});

const addSource = useMutation({
  mutationFn: (request: AddSourceRequest) => api.post('/api/v1/knowledge/data-sources', request),
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ['knowledge', 'data-sources'] });
    toast.success('Source added');
  },
});
```

## Zustand Store
```typescript
// stores/dataSourcesStore.ts
interface DataSourcesState {
  activeTab: string;
  selectedSource: string | null;
  setTab: (tab: string) => void;
  setSource: (id: string | null) => void;
}
```

## Interactions

### View Sources
1. Click Sources tab
2. View source list
3. Check status
4. Manage sources

### Sync Source
1. Click Sync button
2. Start sync process
3. Monitor progress
4. View results

### View Logs
1. Click Logs tab
2. Filter by source/status
3. Click log for details
4. Analyze failures

### Configure Settings
1. Click Settings tab
2. Edit sync frequency
3. Save changes
4. Apply configuration

## Responsive Breakpoints

| Breakpoint | Layout |
|------------|--------|
| Desktop (>1024px) | Full tabs with cards |
| Tablet (768-1024px) | Stacked tabs |
| Mobile (<768px) | Single tab view |

## Loading States
- Sources: Skeleton cards
- Logs: Skeleton table
- Settings: Skeleton form

## Error States
- Sync failure: Error details
- Add failure: Toast error
- Network error: Toast notification

## Accessibility
- Source cards are focusable
- Status announced via `aria-live`
- Screen reader: "Source X, active"
- Keyboard: Enter to select, Tab to navigate

## Telemetry
- `data_sources.view` — Screen loaded
- `data_sources.sync` — Sync triggered
- `data_sources.add` — Source added
- `data_sources.delete` — Source deleted

## Implementation Notes
- Source management with CRUD
- Sync monitoring with progress
- Log viewer for debugging
- AiDock provides data insights
- Export for audit trail
