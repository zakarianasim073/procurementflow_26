# ENT-025: Backup Manager Screen Specification

**Module:** `features/backup-manager/BackupManagerPage`
**Layer:** features
**Version:** 1.0.0
**Status:** Draft
**Workspace:** Settings

## Purpose
Manage system backups, restores, and data protection.

## Screen Layout

```
┌─────────────────────────────────────────────────────────────┐
│ ExecutiveHeader                                             │
├──────────┬──────────────────────────────────────────────────┤
│          │ Breadcrumb: Settings > Backup Manager             │
│ Workspace├──────────────────────────────────────────────────┤
│   Nav    │ BackupManagerHeader (backups, status)            │
│          ├──────────────────────────────────────────────────┤
│          │ BackupManager (main content)                     │
│          │ ┌────────────────────────────────────────────┐   │
│          │ │ BackupStatus (current status)               │   │
│          │ ├────────────────────────────────────────────┤   │
│          │ │ Tabs: [Backups] [Schedule] [Restore]        │   │
│          │ ├────────────────────────────────────────────┤   │
│          │ │ BackupsTab (backup list)                    │   │
│          │ │ ScheduleTab (backup schedule)               │   │
│          │ │ RestoreTab (restore options)                │   │
│          │ └────────────────────────────────────────────┘   │
├──────────┴──────────────────────────────────────────────────┤
│ AiDock (backup recommendations)                             │
└─────────────────────────────────────────────────────────────┘
```

## Component Tree

```
BackupManagerPage
├── ExecutiveHeader
├── Breadcrumb
├── BackupManagerHeader
│   ├── KpiStrip (backup_count, last_backup, next_backup)
│   └── Button (Create Backup)
├── BackupManager
│   ├── BackupStatus
│   │   ├── status_indicator
│   │   ├── last_backup_info
│   │   └── storage_usage
│   ├── Tabs
│   │   ├── BackupsTab
│   │   │   └── BackupList
│   │   │       └── BackupCard × N
│   │   │           ├── name
│   │   │           ├── date
│   │   │           ├── size
│   │   │           ├── status
│   │   │           └── actions (restore, download, delete)
│   │   ├── ScheduleTab
│   │   │   └── ScheduleConfig
│   │   │       ├── frequency
│   │   │       ├── time
│   │   │       ├── retention
│   │   │       └── Button (Save)
│   │   └── RestoreTab
│   │       └── RestoreOptions
│   │           ├── backup_selector
│   │           ├── restore_type
│   │           ├── include_data
│   │           └── Button (Start Restore)
│   └── BackupLogs
│       └── LogEntry × N
│           ├── timestamp
│           ├── event
│           └── status
└── AiDock
    ├── AgentCard (Backup Agent)
    └── EvidencePanel (backup recommendations)
```

## Data Sources

### Backups
```typescript
// API: GET /api/v1/admin/backups
interface BackupList {
  backups: Backup[];
  total_count: number;
  last_backup: string;
  next_backup: string;
  storage_usage: number;
}

interface Backup {
  backup_id: string;
  name: string;
  date: string;
  size: number;
  status: 'completed' | 'in_progress' | 'failed';
  type: 'full' | 'incremental';
  includes: string[];
}
```

### React Query
```typescript
const { data: backups } = useQuery({
  queryKey: ['admin', 'backups'],
  queryFn: () => api.get('/api/v1/admin/backups'),
});

const createBackup = useMutation({
  mutationFn: (request: CreateBackupRequest) => api.post('/api/v1/admin/backups', request),
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ['admin', 'backups'] });
    toast.success('Backup created');
  },
});

const restoreBackup = useMutation({
  mutationFn: ({ backupId, options }: { backupId: string; options: RestoreOptions }) =>
    api.post(`/api/v1/admin/backups/${backupId}/restore`, options),
  onSuccess: () => {
    toast.success('Restore started');
  },
});
```

## Zustand Store
```typescript
// stores/backupManagerStore.ts
interface BackupManagerState {
  activeTab: string;
  setTab: (tab: string) => void;
}
```

## Interactions

### Create Backup
1. Click Create Backup
2. Select type
3. Configure options
4. Start backup

### Restore Backup
1. Click Restore tab
2. Select backup
3. Choose options
4. Start restore

### Schedule Backup
1. Click Schedule tab
2. Set frequency
3. Configure time
4. Save schedule

### Download Backup
1. Click Download button
2. Select format
3. Start download
4. Save file

## Responsive Breakpoints

| Breakpoint | Layout |
|------------|--------|
| Desktop (>1024px) | Full tabs + panels |
| Tablet (768-1024px) | Stacked tabs |
| Mobile (<768px) | Simplified view |

## Loading States
- Backups: Skeleton cards
- Restore: Progress indicator
- Schedule: Loading form

## Error States
- Backup failure: Toast error
- Restore failure: Error details
- Network error: Toast notification

## Accessibility
- Backups are focusable
- Status announced via `aria-live`
- Screen reader: "Backup: Full backup, completed"
- Keyboard: Tab through backups

## Telemetry
- `backup_manager.view` — Screen loaded
- `backup_manager.create` — Backup created
- `backup_manager.restore` — Restore started
- `backup_manager.schedule` — Schedule updated

## Implementation Notes
- Backup management
- Restore functionality
- Schedule configuration
- AiDock provides backup recommendations
- Data protection
