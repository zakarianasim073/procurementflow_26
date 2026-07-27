# ENT-005: Crawler Management Screen Specification

**Module:** `features/crawler/CrawlerManagementPage`
**Layer:** features
**Version:** 1.0.0
**Status:** Draft
**Workspace:** Settings

## Purpose
e-GP crawler monitoring, schedule management, data synchronization, and crawler health tracking.

## Screen Layout

```
┌─────────────────────────────────────────────────────────────┐
│ ExecutiveHeader                                             │
├──────────┬──────────────────────────────────────────────────┤
│          │ Breadcrumb: Settings > Crawler Management         │
│ Workspace├──────────────────────────────────────────────────┤
│   Nav    │ CrawlerHeader (status, last sync)                │
│          ├──────────────────────────────────────────────────┤
│          │ CrawlerManagement (main content)                 │
│          │ ┌────────────────────────────────────────────┐   │
│          │ │ StatusBanner (crawler health)               │   │
│          │ ├────────────────────────────────────────────┤   │
│          │ │ Tabs: [Status] [Schedule] [Logs] [Config]  │   │
│          │ ├────────────────────────────────────────────┤   │
│          │ │ CrawlerStatus (service health)              │   │
│          │ │ ScheduleConfig (cron jobs)                  │   │
│          │ │ SyncLogs (recent activity)                  │   │
│          │ │ Configuration (settings)                    │   │
│          │ └────────────────────────────────────────────┘   │
├──────────┴──────────────────────────────────────────────────┤
│ AiDock (crawler insights, sync recommendations)             │
└─────────────────────────────────────────────────────────────┘
```

## Component Tree

```
CrawlerManagementPage
├── ExecutiveHeader
├── Breadcrumb
├── CrawlerHeader
│   ├── Badge (status: running/stopped/error)
│   ├── KpiStrip (last_sync, items_synced, error_count)
│   └── Button (Sync Now)
├── CrawlerManagement
│   ├── StatusBanner
│   │   ├── Badge (overall health)
│   │   └── last_check timestamp
│   ├── Tabs
│   │   ├── StatusTab
│   │   │   └── CrawlerStatus
│   │   │       ├── ServiceCard (e-GP crawler)
│   │   │       ├── ServiceCard (data processor)
│   │   │       └── ServiceCard (sync service)
│   │   ├── ScheduleTab
│   │   │   └── ScheduleConfig
│   │   │       ├── Table<ScheduleJob>
│   │   │       │   ├── name
│   │   │       │   ├── frequency
│   │   │       │   ├── last_run
│   │   │       │   └── next_run
│   │   │       └── Button (Add Schedule)
│   │   ├── LogsTab
│   │   │   └── SyncLogs
│   │   │       └── Table<SyncLog>
│   │   │           ├── timestamp
│   │   │           ├── action
│   │   │           ├── items
│   │   │           └── status
│   │   └── ConfigTab
│   │       └── ConfigurationForm
│   │           ├── Input (base_url)
│   │           ├── Input (username)
│   │           ├── Input (password)
│   │           ├── Switch (auto_sync)
│   │           └── Button (Save)
│   └── SyncProgress
│       ├── Progress (sync progress)
│       └── Table<SyncItem>
│           ├── tender_id
│           ├── status
│           └── error
└── AiDock
    ├── AgentCard (Acquisition Agent)
    └── EvidencePanel (crawler insights)
```

## Data Sources

### Crawler Status
```typescript
// API: GET /api/v1/admin/crawler/status
interface CrawlerStatus {
  status: 'running' | 'stopped' | 'error';
  services: ServiceStatus[];
  last_sync: string;
  items_synced: number;
  error_count: number;
}

interface ServiceStatus {
  name: string;
  status: 'running' | 'stopped' | 'error';
  last_check: string;
  uptime: number;
  error?: string;
}
```

### Sync Logs
```typescript
// API: GET /api/v1/admin/crawler/logs
interface SyncLogList {
  logs: SyncLog[];
  total_count: number;
}

interface SyncLog {
  log_id: string;
  timestamp: string;
  action: string;
  items_count: number;
  status: 'success' | 'failed' | 'partial';
  error?: string;
  duration: number;
}
```

### React Query
```typescript
const { data: status } = useQuery({
  queryKey: ['admin', 'crawler', 'status'],
  queryFn: () => api.get('/api/v1/admin/crawler/status'),
  refetchInterval: 30_000, // 30 seconds
});

const { data: logs } = useQuery({
  queryKey: ['admin', 'crawler', 'logs', filters],
  queryFn: () => api.get('/api/v1/admin/crawler/logs', { params: filters }),
});

const syncNow = useMutation({
  mutationFn: () => api.post('/api/v1/admin/crawler/sync'),
  onSuccess: () => {
    toast.success('Sync started');
    queryClient.invalidateQueries({ queryKey: ['admin', 'crawler'] });
  },
});
```

## Zustand Store
```typescript
// stores/crawlerManagementStore.ts
interface CrawlerManagementState {
  activeTab: string;
  autoRefresh: boolean;
  setTab: (tab: string) => void;
  setAutoRefresh: (enabled: boolean) => void;
}
```

## Interactions

### Sync Now
1. Click "Sync Now" button
2. Show progress
3. Monitor items synced
4. View results

### View Logs
1. Click Logs tab
2. Filter by date/status
3. Click log for details
4. View error details

### Configure Schedule
1. Click Schedule tab
2. Edit job frequency
3. Add/remove schedules
4. Save configuration

### View Service Health
1. Click Status tab
2. View service cards
3. Check uptime
4. View error details

## Responsive Breakpoints

| Breakpoint | Layout |
|------------|--------|
| Desktop (>1024px) | Full tabs with tables |
| Tablet (768-1024px) | Stacked tabs |
| Mobile (<768px) | Single tab view |

## Loading States
- Status: Skeleton cards
- Logs: Skeleton table
- Config: Skeleton form

## Error States
- Sync failure: Error details
- Service down: Warning banner
- Network error: Retry button

## Accessibility
- Service cards are focusable
- Status changes announced via `aria-live`
- Screen reader: "Service X: running"
- Keyboard: Enter to view details

## Telemetry
- `crawler_management.view` — Screen loaded
- `crawler_management.sync` — Sync triggered
- `crawler_management.config_change` — Config updated

## Implementation Notes
- Real-time status monitoring
- Sync logs with filtering
- Schedule configuration
- AiDock provides crawler insights
- Service health tracking
