# EXEC-004: Settings Overview Screen Specification

**Module:** `features/settings/SettingsOverviewPage`
**Layer:** features
**Version:** 1.0.0
**Status:** Draft
**Workspace:** Settings

## Purpose
Central settings hub with quick access to all configuration areas and system status overview.

## Screen Layout

```
┌─────────────────────────────────────────────────────────────┐
│ ExecutiveHeader                                             │
├──────────┬──────────────────────────────────────────────────┤
│          │ Breadcrumb: Settings                              │
│ Workspace├──────────────────────────────────────────────────┤
│   Nav    │ SettingsOverviewHeader (system status)           │
│          ├──────────────────────────────────────────────────┤
│          │ SettingsOverview (main content)                  │
│          │ ┌────────────────────────────────────────────┐   │
│          │ │ SystemStatus (health overview)              │   │
│          │ ├────────────────────────────────────────────┤   │
│          │ │ SettingsGrid (category cards)               │   │
│          │ │ ┌──────────┐ ┌──────────┐ ┌──────────┐     │   │
│          │ │ │ Profile  │ │ Team     │ │ Security │     │   │
│          │ │ └──────────┘ └──────────┘ └──────────┘     │   │
│          │ │ ┌──────────┐ ┌──────────┐ ┌──────────┐     │   │
│          │ │ │ Notif    │ │ SOR      │ │ Crawler  │     │   │
│          │ │ └──────────┘ └──────────┘ └──────────┘     │   │
│          │ ├────────────────────────────────────────────┤   │
│          │ │ QuickActions (common tasks)                 │   │
│          │ └────────────────────────────────────────────┘   │
├──────────┴──────────────────────────────────────────────────┤
│ AiDock (settings insights, recommendations)                 │
└─────────────────────────────────────────────────────────────┘
```

## Component Tree

```
SettingsOverviewPage
├── ExecutiveHeader
├── Breadcrumb
├── SettingsOverviewHeader
│   ├── Badge (system_status)
│   └── KpiStrip (uptime, users, storage)
├── SettingsOverview
│   ├── SystemStatus
│   │   ├── Badge (health: healthy/degraded/unhealthy)
│   │   ├── KpiCard (uptime)
│   │   ├── KpiCard (active_users)
│   │   └── KpiCard (storage_used)
│   ├── SettingsGrid
│   │   └── SettingsCard × N
│   │       ├── icon
│   │       ├── title
│   │       ├── description
│   │       └── Button (Configure)
│   └── QuickActions
│       ├── Button (Invite User)
│       ├── Button (Sync Data)
│       ├── Button (Export Report)
│       └── Button (Run Validation)
└── AiDock
    ├── AgentCard (Admin Agent)
    └── EvidencePanel (settings insights)
```

## Data Sources

### System Status
```typescript
// API: GET /api/v1/admin/system/status
interface SystemStatus {
  status: 'healthy' | 'degraded' | 'unhealthy';
  uptime: number;
  active_users: number;
  storage_used: number;
  storage_total: number;
  last_backup: string;
  version: string;
}
```

### Settings Categories
```typescript
// API: GET /api/v1/admin/settings
interface SettingsCategory {
  category_id: string;
  name: string;
  description: string;
  icon: string;
  configured: boolean;
  last_updated: string;
}
```

### React Query
```typescript
const { data: status } = useQuery({
  queryKey: ['admin', 'system', 'status'],
  queryFn: () => api.get('/api/v1/admin/system/status'),
  refetchInterval: 60_000, // 1 minute
});

const { data: categories } = useQuery({
  queryKey: ['admin', 'settings'],
  queryFn: () => api.get('/api/v1/admin/settings'),
});
```

## Zustand Store
```typescript
// stores/settingsOverviewStore.ts
interface SettingsOverviewState {
  selectedCategory: string | null;
  setCategory: (id: string | null) => void;
}
```

## Interactions

### Category Click
1. Click SettingsCard
2. Navigate to category page
3. Preserve state
4. Load category settings

### Quick Action
1. Click action button
2. Execute action
3. Show progress
4. Show result

### System Status
1. View health badge
2. Click for details
3. View metrics
4. Export status report

## Responsive Breakpoints

| Breakpoint | Layout |
|------------|--------|
| Desktop (>1024px) | Grid cards + status |
| Tablet (768-1024px) | Stacked cards |
| Mobile (<768px) | Single column, list view |

## Loading States
- Status: Skeleton cards
- Categories: Skeleton grid
- Actions: Button spinners

## Error States
- Status check failure: Warning
- Action failure: Toast error
- Network error: Retry button

## Accessibility
- Cards are focusable
- Status announced via `aria-live`
- Screen reader: "System status: healthy"
- Keyboard: Enter to select, Tab to navigate

## Telemetry
- `settings_overview.view` — Screen loaded
- `settings_overview.category_click` — Category selected
- `settings_overview.quick_action` — Action executed

## Implementation Notes
- Central hub for all settings
- System status overview
- Quick access to common tasks
- AiDock provides settings insights
- Category cards for navigation
