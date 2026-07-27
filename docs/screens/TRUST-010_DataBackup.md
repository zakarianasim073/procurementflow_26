# TRUST-010: Data Backup Screen Specification

**Module:** `features/data-backup/DataBackupPage`
**Layer:** features
**Version:** 1.0.0
**Status:** Draft
**Workspace:** Trust

## Purpose
Data backup management, recovery operations, and disaster recovery planning.

## Screen Layout

```
┌─────────────────────────────────────────────────────────────┐
│ ExecutiveHeader                                             │
├──────────┬──────────────────────────────────────────────────┤
│          │ Breadcrumb: Trust > Data Backup                   │
│ Workspace├──────────────────────────────────────────────────┤
│   Nav    │ DataBackupHeader (status, last backup)           │
│          ├──────────────────────────────────────────────────┤
│          │ DataBackup (main content)                        │
│          │ ┌────────────────────────────────────────────┐   │
│          │ │ StatusBanner (backup health)                │   │
│          │ ├────────────────────────────────────────────┤   │
│          │ │ Tabs: [Backups] [Schedule] [Restore] [Logs]│   │
│          │ ├────────────────────────────────────────────┤   │
│          │ │ BackupList (backup cards)                   │   │
│          │ │ ScheduleConfig (cron jobs)                  │   │
│          │ │ RestoreWizard (recovery process)            │   │
│          │ │ OperationLogs (backup/restore history)      │   │
│          │ └────────────────────────────────────────────┘   │
├──────────┴──────────────────────────────────────────────────┤
│ AiDock (backup insights, recovery suggestions)              │
└─────────────────────────────────────────────────────────────┘
```

## Component Tree

```
DataBackupPage
├── ExecutiveHeader
├── Breadcrumb
├── DataBackupHeader
│   ├── Badge (status: healthy/warning/critical)
│   ├── KpiStrip (last_backup, backup_count, storage_used)
│   └── Button (Create Backup)
├── DataBackup
│   ├── StatusBanner
│   │   ├── Badge (health status)
│   │   └── last_check timestamp
│   ├── Tabs
│   │   ├── BackupsTab
│   │   │   └── BackupList
│   │   │       └── BackupCard × N
│   │   │           ├── name
│   │   │           ├── created_at
│   │   │           ├── size
│   │   │           ├── status
│   │   │           └── Button (Restore/Download)
│   │   ├── ScheduleTab
│   │   │   └── ScheduleConfig
│   │   │       ├── Table<ScheduleJob>
│   │   │       │   ├── frequency
│   │   │       │   ├── last_run
│   │   │       │   └── next_run
│   │   │       └── Button (Add Schedule)
│   │   ├── RestoreTab
│   │   │   └── RestoreWizard
│   │   │       ├── Step1_Select
│   │   │       │   └── BackupSelector
│   │   │       ├── Step2_Configure
│   │   │       │   └── RestoreOptions
│   │   │       └── Step3_Execute
│   │   │           └── RestoreProgress
│   │   └── LogsTab
│   │       └── OperationLogs
│   │           └── Table<BackupLog>
│   │               ├── timestamp
│   │               ├── action
│   │               ├── status
│   │               └── duration
│   └── BackupSettings
│       ├── Switch (auto_backup)
│       ├── Select (frequency)
│       ├── Input (retention_days)
│       └── Button (Save)
└── AiDock
    ├── AgentCard (Admin Agent)
    └── EvidencePanel (backup insights)
```

## Data Sources

### Backups
```typescript
// API: GET /api/v1/admin/backups
interface BackupList {
  backups: Backup[];
  total_count: number;
  storage_used: number;
}

interface Backup {
  backup_id: string;
  name: string;
  created_at: string;
  size: number;
  status: 'completed' | 'in_progress' | 'failed';
  type: 'manual' | 'scheduled' | 'auto';
  includes: string[];
}
```

### Backup Schedule
```typescript
// API: GET /api/v1/admin/backups/schedule
interface ScheduleConfig {
  auto_backup: boolean;
  frequency: 'daily' | 'weekly' | 'monthly';
  retention_days: number;
  next_run: string;
  last_run: string;
}
```

### React Query
```typescript
const { data: backups } = useQuery({
  queryKey: ['admin', 'backups'],
  queryFn: () => api.get('/api/v1/admin/backups'),
});

const { data: schedule } = useQuery({
  queryKey: ['admin', 'backups', 'schedule'],
  queryFn: () => api.get('/api/v1/admin/backups/schedule'),
});

const createBackup = useMutation({
  mutationFn: () => api.post('/api/v1/admin/backups'),
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ['admin', 'backups'] });
    toast.success('Backup created');
  },
});

const restoreBackup = useMutation({
  mutationFn: (backupId: string) => api.post(`/api/v1/admin/backups/${backupId}/restore`),
  onSuccess: () => {
    toast.success('Restore completed');
    window.location.reload();
  },
});
```

## Zustand Store
```typescript
// stores/dataBackupStore.ts
interface DataBackupState {
  activeTab: string;
  selectedBackup: string | null;
  setTab: (tab: string) => void;
  setBackup: (id: string | null) => void;
}
```

## Interactions

### Create Backup
1. Click "Create Backup"
2. Show progress
3. Add to backup list
4. Show success

### Restore Backup
1. Click Restore button
2. Open RestoreWizard
3. Select backup
4. Configure options
5. Execute restore
6. Reload system

### Download Backup
1. Click Download button
2. Generate download link
3. Download file
4. Show progress

### Update Schedule
1. Edit schedule settings
2. Save changes
3. Update next run
4. Confirm update

## Responsive Breakpoints

| Breakpoint | Layout |
|------------|--------|
| Desktop (>1024px) | Full tabs with cards |
| Tablet (768-1024px) | Stacked tabs |
| Mobile (<768px) | Single tab view |

## Loading States
- Backups: Skeleton cards
- Schedule: Skeleton form
- Restore: Progress indicator

## Error States
- Backup failure: Error details
- Restore failure: Rollback
- Network error: Toast notification

## Accessibility
- Backup cards are focusable
- Status announced via `aria-live`
- Screen reader: "Backup X, completed"
- Keyboard: Enter to select, Tab to navigate

## Telemetry
- `data_backup.view` — Screen loaded
- `data_backup.create` — Backup created
- `data_backup.restore` — Restore executed
- `data_backup.schedule_update` — Schedule updated

## Implementation Notes
- Backup list with status
- Schedule configuration
- Step-by-step restore wizard
- AiDock provides backup insights
- Export for disaster recovery
