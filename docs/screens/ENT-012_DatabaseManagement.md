# ENT-012: Database Management Screen Specification

**Module:** `features/database/DatabaseManagementPage`
**Layer:** features
**Version:** 1.0.0
**Status:** Draft
**Workspace:** Settings

## Purpose
Database monitoring, query analysis, and maintenance operations.

## Screen Layout

```
┌─────────────────────────────────────────────────────────────┐
│ ExecutiveHeader                                             │
├──────────┬──────────────────────────────────────────────────┤
│          │ Breadcrumb: Settings > Database Management        │
│ Workspace├──────────────────────────────────────────────────┤
│   Nav    │ DatabaseManagementHeader (status, size)          │
│          ├──────────────────────────────────────────────────┤
│          │ DatabaseManagement (main content)                │
│          │ ┌────────────────────────────────────────────┐   │
│          │ │ Tabs: [Overview] [Tables] [Queries] [Backup]│  │
│          │ ├────────────────────────────────────────────┤   │
│          │ │ DatabaseOverview (size, connections)        │   │
│          │ │ TableList (table sizes, row counts)         │   │
│          │ │ QueryAnalyzer (slow queries)                │   │
│          │ │ BackupManager (backup/restore)              │   │
│          │ └────────────────────────────────────────────┘   │
├──────────┴──────────────────────────────────────────────────┤
│ AiDock (database insights, optimization)                    │
└─────────────────────────────────────────────────────────────┘
```

## Component Tree

```
DatabaseManagementPage
├── ExecutiveHeader
├── Breadcrumb
├── DatabaseManagementHeader
│   ├── KpiStrip (db_size, table_count, connection_count)
│   └── Button (Run Maintenance)
├── DatabaseManagement
│   ├── Tabs
│   │   ├── OverviewTab
│   │   │   └── DatabaseOverview
│   │   │       ├── KpiCard (db_size)
│   │   │       ├── KpiCard (table_count)
│   │   │       ├── KpiCard (connection_count)
│   │   │       └── Chart (size_trend)
│   │   ├── TablesTab
│   │   │   └── TableList
│   │   │       └── Table<DatabaseTable>
│   │   │           ├── name
│   │   │           ├── row_count
│   │   │           ├── size
│   │   │           └── last_vacuum
│   │   ├── QueriesTab
│   │   │   └── QueryAnalyzer
│   │   │       ├── Table<SlowQuery>
│   │   │       │   ├── query
│   │   │       │   ├── avg_time
│   │   │       │   ├── calls
│   │   │       │   └── suggestions
│   │   │       └── Button (Analyze)
│   │   └── BackupTab
│   │       └── BackupManager
│   │           ├── BackupList
│   │           │   └── BackupCard × N
│   │           │       ├── name
│   │           │       ├── size
│   │           │       └── Button (Restore)
│   │           └── Button (Create Backup)
│   └── DatabaseActions
│       ├── Button (Vacuum)
│       ├── Button (Analyze Tables)
│       └── Button (Export Schema)
└── AiDock
    ├── AgentCard (Database Agent)
    └── EvidencePanel (database insights)
```

## Data Sources

### Database Overview
```typescript
// API: GET /api/v1/admin/database/overview
interface DatabaseOverview {
  db_size: number;
  table_count: number;
  connection_count: number;
  active_queries: number;
  size_trend: { date: string; size: number }[];
}

interface DatabaseTable {
  name: string;
  row_count: number;
  size: number;
  last_vacuum?: string;
  last_analyze?: string;
}
```

### Slow Queries
```typescript
// API: GET /api/v1/admin/database/queries
interface SlowQueryList {
  queries: SlowQuery[];
}

interface SlowQuery {
  query_id: string;
  query: string;
  avg_time: number;
  calls: number;
  total_time: number;
  suggestions: string[];
}
```

### React Query
```typescript
const { data: overview } = useQuery({
  queryKey: ['admin', 'database', 'overview'],
  queryFn: () => api.get('/api/v1/admin/database/overview'),
  refetchInterval: 60_000, // 1 minute
});

const { data: tables } = useQuery({
  queryKey: ['admin', 'database', 'tables'],
  queryFn: () => api.get('/api/v1/admin/database/tables'),
});

const { data: queries } = useQuery({
  queryKey: ['admin', 'database', 'queries'],
  queryFn: () => api.get('/api/v1/admin/database/queries'),
});

const runVacuum = useMutation({
  mutationFn: () => api.post('/api/v1/admin/database/vacuum'),
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ['admin', 'database'] });
    toast.success('Vacuum completed');
  },
});
```

## Zustand Store
```typescript
// stores/databaseManagementStore.ts
interface DatabaseManagementState {
  activeTab: string;
  setTab: (tab: string) => void;
}
```

## Interactions

### View Overview
1. Click Overview tab
2. View database size
3. Check connections
4. Analyze trends

### Analyze Tables
1. Click Tables tab
2. View table sizes
3. Check row counts
4. Review vacuum status

### Optimize Queries
1. Click Queries tab
2. View slow queries
3. Review suggestions
4. Apply optimizations

### Manage Backups
1. Click Backup tab
2. View backup list
3. Create new backup
4. Restore if needed

## Responsive Breakpoints

| Breakpoint | Layout |
|------------|--------|
| Desktop (>1024px) | Full tabs with tables |
| Tablet (768-1024px) | Stacked tabs |
| Mobile (<768px) | Single tab view |

## Loading States
- Overview: Skeleton cards
- Tables: Skeleton table
- Queries: Skeleton table

## Error States
- Vacuum failure: Toast error
- Query failure: Retry button
- Network error: Toast notification

## Accessibility
- Tables are focusable
- Stats announced via `aria-live`
- Screen reader: "DB size: 1.2GB"
- Keyboard: Tab through elements

## Telemetry
- `database_management.view` — Screen loaded
- `database_management.vacuum` — Vacuum run
- `database_management.backup` — Backup created
- `database_management.restore` — Restore executed

## Implementation Notes
- Database size monitoring
- Table analysis
- Query optimization
- Backup management
- AiDock provides database insights
