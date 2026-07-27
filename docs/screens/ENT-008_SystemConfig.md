# ENT-008: System Configuration Screen Specification

**Module:** `features/system-config/SystemConfigPage`
**Layer:** features
**Version:** 1.0.0
**Status:** Draft
**Workspace:** Settings

## Purpose
System-wide configuration, feature flags, and environment settings management.

## Screen Layout

```
┌─────────────────────────────────────────────────────────────┐
│ ExecutiveHeader                                             │
├──────────┬──────────────────────────────────────────────────┤
│          │ Breadcrumb: Settings > System Configuration       │
│ Workspace├──────────────────────────────────────────────────┤
│   Nav    │ SystemConfigHeader (version, environment)        │
│          ├──────────────────────────────────────────────────┤
│          │ SystemConfig (main content)                      │
│          │ ┌────────────────────────────────────────────┐   │
│          │ │ Tabs: [General] [Features] [API] [Backup]  │   │
│          │ ├────────────────────────────────────────────┤   │
│          │ │ GeneralSettings (basic config)              │   │
│          │ │ FeatureFlags (toggle features)              │   │
│          │ │ ApiSettings (API configuration)             │   │
│          │ │ BackupSettings (backup/restore)             │   │
│          │ └────────────────────────────────────────────┘   │
├──────────┴──────────────────────────────────────────────────┤
│ AiDock (config insights, optimization)                      │
└─────────────────────────────────────────────────────────────┘
```

## Component Tree

```
SystemConfigPage
├── ExecutiveHeader
├── Breadcrumb
├── SystemConfigHeader
│   ├── Badge (version)
│   ├── Badge (environment: dev/staging/prod)
│   └── Button (Save All)
├── SystemConfig
│   ├── Tabs
│   │   ├── GeneralTab
│   │   │   └── GeneralSettings
│   │   │       ├── Input (site_name)
│   │   │       ├── Input (site_url)
│   │   │       ├── Select (timezone)
│   │   │       ├── Select (language)
│   │   │       └── Switch (maintenance_mode)
│   │   ├── FeaturesTab
│   │   │   └── FeatureFlags
│   │   │       └── FeatureFlag × N
│   │   │           ├── name
│   │   │           ├── description
│   │   │           ├── enabled
│   │   │           └── Switch (toggle)
│   │   ├── ApiTab
│   │   │   └── ApiSettings
│   │   │       ├── Input (rate_limit)
│   │   │       ├── Input (timeout)
│   │   │       ├── Input (max_retries)
│   │   │       └── Button (Test Connection)
│   │   └── BackupTab
│   │       └── BackupSettings
│   │           ├── Table<Backup>
│   │           │   ├── name
│   │           │   ├── created_at
│   │           │   ├── size
│   │           │   └── Button (Restore)
│   │           └── Button (Create Backup)
│   └── ConfigEditor
│       ├── CodeEditor (raw config)
│       └── Button (Apply)
└── AiDock
    ├── AgentCard (Admin Agent)
    └── EvidencePanel (config insights)
```

## Data Sources

### System Configuration
```typescript
// API: GET /api/v1/admin/config
interface SystemConfig {
  general: GeneralConfig;
  features: FeatureFlag[];
  api: ApiConfig;
  backup: BackupConfig;
}

interface GeneralConfig {
  site_name: string;
  site_url: string;
  timezone: string;
  language: string;
  maintenance_mode: boolean;
}

interface FeatureFlag {
  flag_id: string;
  name: string;
  description: string;
  enabled: boolean;
  environment: string;
}

interface ApiConfig {
  rate_limit: number;
  timeout: number;
  max_retries: number;
  cors_origins: string[];
}

interface BackupConfig {
  auto_backup: boolean;
  backup_frequency: string;
  retention_days: number;
}
```

### Backups
```typescript
// API: GET /api/v1/admin/config/backups
interface BackupList {
  backups: Backup[];
}

interface Backup {
  backup_id: string;
  name: string;
  created_at: string;
  size: number;
  status: 'completed' | 'in_progress' | 'failed';
}
```

### React Query
```typescript
const { data: config } = useQuery({
  queryKey: ['admin', 'config'],
  queryFn: () => api.get('/api/v1/admin/config'),
});

const { data: backups } = useQuery({
  queryKey: ['admin', 'config', 'backups'],
  queryFn: () => api.get('/api/v1/admin/config/backups'),
});

const saveConfig = useMutation({
  mutationFn: (request: SaveConfigRequest) => api.patch('/api/v1/admin/config', request),
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ['admin', 'config'] });
    toast.success('Configuration saved');
  },
});

const createBackup = useMutation({
  mutationFn: () => api.post('/api/v1/admin/config/backups'),
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ['admin', 'config', 'backups'] });
    toast.success('Backup created');
  },
});

const restoreBackup = useMutation({
  mutationFn: (backupId: string) => api.post(`/api/v1/admin/config/backups/${backupId}/restore`),
  onSuccess: () => {
    toast.success('Backup restored');
    window.location.reload();
  },
});
```

## Zustand Store
```typescript
// stores/systemConfigStore.ts
interface SystemConfigState {
  activeTab: string;
  hasUnsavedChanges: boolean;
  setTab: (tab: string) => void;
  setUnsavedChanges: (hasChanges: boolean) => void;
}
```

## Interactions

### Edit Configuration
1. Modify settings
2. Mark as unsaved
3. Click Save
4. Apply changes

### Toggle Feature Flag
1. Click switch
2. Toggle flag
3. Auto-save
4. Update feature

### Create Backup
1. Click "Create Backup"
2. Show progress
3. Add to backup list
4. Show success

### Restore Backup
1. Click Restore button
2. Confirm restore
3. Apply backup
4. Reload system

## Responsive Breakpoints

| Breakpoint | Layout |
|------------|--------|
| Desktop (>1024px) | Full tabs with forms |
| Tablet (768-1024px) | Stacked tabs |
| Mobile (<768px) | Single tab view |

## Loading States
- Config: Skeleton form
- Features: Skeleton switches
- Backups: Skeleton table

## Error States
- Save failure: Toast error
- Restore failure: Rollback
- Network error: Retry button

## Accessibility
- Form fields are focusable
- Changes announced via `aria-live`
- Screen reader: "Feature X: enabled"
- Keyboard: Tab through fields, Enter to save

## Telemetry
- `system_config.view` — Screen loaded
- `system_config.save` — Config saved
- `system_config.feature_toggle` — Feature toggled
- `system_config.backup` — Backup created
- `system_config.restore` — Backup restored

## Implementation Notes
- 4 tabs for different config areas
- Feature flags for gradual rollout
- Backup/restore for disaster recovery
- AiDock provides config insights
- Raw config editor for advanced users
