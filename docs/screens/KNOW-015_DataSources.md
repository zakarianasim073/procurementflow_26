# KNOW-015: Data Sources Screen Specification

**Module:** `features/data-sources/DataSourcesPage`
**Layer:** features
**Version:** 1.0.0
**Status:** Draft
**Workspace:** Knowledge

## Purpose
Manage data sources, connections, and data pipeline configuration.

## Screen Layout

```
┌─────────────────────────────────────────────────────────────┐
│ ExecutiveHeader                                             │
├──────────┬──────────────────────────────────────────────────┤
│          │ Breadcrumb: Knowledge > Data Sources              │
│ Workspace├──────────────────────────────────────────────────┤
│   Nav    │ DataSourcesHeader (sources, status)              │
│          ├──────────────────────────────────────────────────┤
│          │ DataSources (main content)                       │
│          │ ┌────────────────────────────────────────────┐   │
│          │ │ DataSourceList (data sources)               │   │
│          │ │ ┌──────────────────────────────────────────┐│   │
│          │ │ │ Source: PostgreSQL  [Connected]          ││   │
│          │ │ │ Source: e-GP API    [Active]             ││   │
│          │ │ │ Source: SOR PDFs    [Syncing]            ││   │
│          │ │ └──────────────────────────────────────────┘│   │
│          │ ├────────────────────────────────────────────┤   │
│          │ │ DataSourceDetails (selected source)         │   │
│          │ └────────────────────────────────────────────┘   │
├──────────┴──────────────────────────────────────────────────┤
│ AiDock (data source insights)                               │
└─────────────────────────────────────────────────────────────┘
```

## Component Tree

```
DataSourcesPage
├── ExecutiveHeader
├── Breadcrumb
├── DataSourcesHeader
│   ├── KpiStrip (source_count, active_count, sync_count)
│   └── Button (Add Source)
├── DataSources
│   ├── DataSourceList
│   │   └── DataSourceCard × N
│   │       ├── name
│   │       ├── type
│   │       ├── status
│   │       ├── last_sync
│   │       └── Button (Configure)
│   ├── DataSourceDetails
│   │   ├── connection_info
│   │   ├── sync_status
│   │   ├── data_quality
│   │   └── configuration
│   ├── SyncHistory
│   │   └── SyncEntry × N
│   │       ├── timestamp
│   │       ├── status
│   │       ├── records
│   │       └── duration
│   └── DataQuality
│       ├── completeness
│       ├── accuracy
│       └── timeliness
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
  active_count: number;
}

interface DataSource {
  source_id: string;
  name: string;
  type: 'database' | 'api' | 'file' | 'webhook';
  status: 'active' | 'inactive' | 'syncing' | 'error';
  connection: ConnectionConfig;
  last_sync: string;
  sync_frequency: string;
  data_quality: DataQuality;
}

interface ConnectionConfig {
  host?: string;
  port?: number;
  database?: string;
  api_url?: string;
  credentials?: Record<string, any>;
}

interface DataQuality {
  completeness: number;
  accuracy: number;
  timeliness: number;
}
```

### React Query
```typescript
const { data: sources } = useQuery({
  queryKey: ['knowledge', 'data-sources'],
  queryFn: () => api.get('/api/v1/knowledge/data-sources'),
});

const { data: sourceDetails } = useQuery({
  queryKey: ['knowledge', 'data-sources', sourceId],
  queryFn: () => api.get(`/api/v1/knowledge/data-sources/${sourceId}`),
  enabled: !!sourceId,
});

const syncSource = useMutation({
  mutationFn: (sourceId: string) => api.post(`/api/v1/knowledge/data-sources/${sourceId}/sync`),
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ['knowledge', 'data-sources'] });
    toast.success('Sync started');
  },
});
```

## Zustand Store
```typescript
// stores/dataSourcesStore.ts
interface DataSourcesState {
  selectedSource: string | null;
  setSource: (id: string | null) => void;
}
```

## Interactions

### View Sources
1. Click source card
2. View details
3. Check status
4. Review quality

### Sync Source
1. Click Sync button
2. Start sync
3. Monitor progress
4. View results

### Configure Source
1. Click Configure
2. Edit settings
3. Test connection
4. Save changes

### View History
1. Click History tab
2. View sync entries
3. Check status
4. Analyze duration

## Responsive Breakpoints

| Breakpoint | Layout |
|------------|--------|
| Desktop (>1024px) | Full list + details |
| Tablet (768-1024px) | List with modal details |
| Mobile (<768px) | Simplified list |

## Loading States
- Sources: Skeleton cards
- Details: Loading spinner
- Sync: Progress indicator

## Error States
- Connection failure: Retry button
- Sync failure: Error details
- Network error: Toast notification

## Accessibility
- Sources are focusable
- Status announced via `aria-live`
- Screen reader: "Source: PostgreSQL, status: connected"
- Keyboard: Tab through sources

## Telemetry
- `data_sources.view` — Screen loaded
- `data_sources.sync` — Source synced
- `data_sources.configure` — Source configured
- `data_sources.view_details` — Details viewed

## Implementation Notes
- Multiple data source types
- Real-time sync monitoring
- Data quality metrics
- AiDock provides data insights
- Export for analysis
