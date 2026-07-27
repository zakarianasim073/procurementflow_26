# ENT-027: System Information Screen Specification

**Module:** `features/system-information/SystemInformationPage`
**Layer:** features
**Version:** 1.0.0
**Status:** Draft
**Workspace:** Settings

## Purpose
Display system information, configuration, and environment details.

## Screen Layout

```
┌─────────────────────────────────────────────────────────────┐
│ ExecutiveHeader                                             │
├──────────┬──────────────────────────────────────────────────┤
│          │ Breadcrumb: Settings > System Information         │
│ Workspace├──────────────────────────────────────────────────┤
│   Nav    │ SystemInformationHeader (version, status)        │
│          ├──────────────────────────────────────────────────┤
│          │ SystemInformation (main content)                 │
│          │ ┌────────────────────────────────────────────┐   │
│          │ │ Tabs: [Overview] [Config] [Environment]    │   │
│          │ ├────────────────────────────────────────────┤   │
│          │ │ OverviewTab (system summary)                │   │
│          │ │ ConfigTab (configuration)                   │   │
│          │ │ EnvironmentTab (environment)                │   │
│          │ └────────────────────────────────────────────┘   │
├──────────┴──────────────────────────────────────────────────┤
│ AiDock (system insights)                                    │
└─────────────────────────────────────────────────────────────┘
```

## Component Tree

```
SystemInformationPage
├── ExecutiveHeader
├── Breadcrumb
├── SystemInformationHeader
│   ├── KpiStrip (version, uptime, health_score)
│   └── Button (Export Info)
├── SystemInformation
│   ├── Tabs
│   │   ├── OverviewTab
│   │   │   ├── SystemSummary
│   │   │   │   ├── version
│   │   │   │   ├── build
│   │   │   │   ├── uptime
│   │   │   │   └── health_score
│   │   │   ├── ComponentStatus
│   │   │   │   └── Component × N
│   │   │   │       ├── name
│   │   │   │       ├── status
│   │   │   │       └── version
│   │   │   └── SystemStats
│   │   │       ├── chart (uptime_history)
│   │   │       └── chart (performance_trend)
│   │   ├── ConfigTab
│   │   │   └── ConfigList
│   │   │       └── ConfigItem × N
│   │   │           ├── key
│   │   │           ├── value
│   │   │           ├── source
│   │   │           └── Button (Edit)
│   │   └── EnvironmentTab
│   │       └── EnvironmentList
│   │           └── EnvItem × N
│   │               ├── name
│   │               ├── value
│   │               ├── type
│   │               └── is_secret
│   └── SystemLogs
│       └── LogEntry × N
│           ├── timestamp
│           ├── level
│           └── message
└── AiDock
    ├── AgentCard (System Agent)
    └── EvidencePanel (system insights)
```

## Data Sources

### System Information
```typescript
// API: GET /api/v1/admin/system/info
interface SystemInfo {
  version: string;
  build: string;
  uptime: number;
  health_score: number;
  components: ComponentStatus[];
  config: ConfigItem[];
  environment: EnvItem[];
}

interface ComponentStatus {
  name: string;
  status: 'healthy' | 'degraded' | 'down';
  version: string;
  last_check: string;
}

interface ConfigItem {
  key: string;
  value: any;
  source: string;
  editable: boolean;
}

interface EnvItem {
  name: string;
  value: string;
  type: string;
  is_secret: boolean;
}
```

### React Query
```typescript
const { data: systemInfo } = useQuery({
  queryKey: ['admin', 'system', 'info'],
  queryFn: () => api.get('/api/v1/admin/system/info'),
});
```

## Zustand Store
```typescript
// stores/systemInformationStore.ts
interface SystemInformationState {
  activeTab: string;
  setTab: (tab: string) => void;
}
```

## Interactions

### View Overview
1. Click Overview tab
2. View summary
3. Check components
4. Review stats

### Edit Config
1. Click Config tab
2. Find config item
3. Click Edit
4. Modify value

### View Environment
1. Click Environment tab
2. View env vars
3. Check types
4. Note secrets

### Export Info
1. Click Export
2. Choose format
3. Include all sections
4. Download file

## Responsive Breakpoints

| Breakpoint | Layout |
|------------|--------|
| Desktop (>1024px) | Full tabs + panels |
| Tablet (768-1024px) | Stacked tabs |
| Mobile (<768px) | Simplified view |

## Loading States
- System: Loading info
- Config: Loading items
- Environment: Loading vars

## Error States
- Load failure: Retry button
- Edit failure: Toast error
- Network error: Toast notification

## Accessibility
- Items are focusable
- Status announced via `aria-live`
- Screen reader: "Component: API, status: healthy"
- Keyboard: Tab through items

## Telemetry
- `system_information.view` — Screen loaded
- `system_information.config_edit` — Config edited
- `system_information.export` — Info exported

## Implementation Notes
- System information display
- Configuration management
- Environment variables
- AiDock provides system insights
- Export for documentation
