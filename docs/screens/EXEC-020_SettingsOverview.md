# EXEC-020: Settings Overview Screen Specification

**Module:** `features/settings-overview/SettingsOverviewPage`
**Layer:** features
**Version:** 1.0.0
**Status:** Draft
**Workspace:** Dashboard

## Purpose
Overview of system settings, configuration, and preferences.

## Screen Layout

```
┌─────────────────────────────────────────────────────────────┐
│ ExecutiveHeader                                             │
├──────────┬──────────────────────────────────────────────────┤
│          │ Breadcrumb: Dashboard > Settings Overview         │
│ Workspace├──────────────────────────────────────────────────┤
│   Nav    │ SettingsOverviewHeader (settings, changes)       │
│          ├──────────────────────────────────────────────────┤
│          │ SettingsOverview (main content)                  │
│          │ ┌────────────────────────────────────────────┐   │
│          │ │ SettingsGrid (setting categories)           │   │
│          │ │ ┌──────┬──────┬──────┬──────┐              │   │
│          │ │ │General│Security│Notify│Backup│              │   │
│          │ │ │      │       │      │      │              │   │
│          │ │ └──────┴──────┴──────┴──────┘              │   │
│          │ ├────────────────────────────────────────────┤   │
│          │ │ RecentChanges (recent modifications)        │   │
│          │ └────────────────────────────────────────────┘   │
├──────────┴──────────────────────────────────────────────────┤
│ AiDock (settings suggestions)                               │
└─────────────────────────────────────────────────────────────┘
```

## Component Tree

```
SettingsOverviewPage
├── ExecutiveHeader
├── Breadcrumb
├── SettingsOverviewHeader
│   ├── KpiStrip (setting_count, pending_changes)
│   └── Button (Export Settings)
├── SettingsOverview
│   ├── SettingsGrid
│   │   └── SettingsCard × N
│   │       ├── icon
│   │       ├── name
│   │       ├── description
│   │       ├── status
│   │       └── Button (Configure)
│   ├── RecentChanges
│   │   └── ChangeCard × N
│   │       ├── setting
│   │       ├── old_value
│   │       ├── new_value
│   │       ├── changed_by
│   │       └── timestamp
│   ├── SettingsSearch
│   │   ├── SearchBar
│   │   └── SearchResults
│   │       └── SearchResult × N
│   └── SettingsHealth
│       ├── health_score
│       ├── issues
│       └── recommendations
└── AiDock
    ├── AgentCard (Settings Agent)
    └── EvidencePanel (settings suggestions)
```

## Data Sources

### Settings Overview
```typescript
// API: GET /api/v1/admin/settings/overview
interface SettingsOverview {
  categories: SettingsCategory[];
  recent_changes: SettingsChange[];
  health: SettingsHealth;
}

interface SettingsCategory {
  category_id: string;
  name: string;
  description: string;
  icon: string;
  settings_count: number;
  status: 'configured' | 'default' | 'warning';
}

interface SettingsChange {
  change_id: string;
  setting: string;
  old_value: any;
  new_value: any;
  changed_by: string;
  changed_at: string;
}

interface SettingsHealth {
  score: number;
  issues: string[];
  recommendations: string[];
}
```

### React Query
```typescript
const { data: overview } = useQuery({
  queryKey: ['admin', 'settings', 'overview'],
  queryFn: () => api.get('/api/v1/admin/settings/overview'),
});
```

## Zustand Store
```typescript
// stores/settingsOverviewStore.ts
interface SettingsOverviewState {
  searchQuery: string;
  setSearch: (query: string) => void;
}
```

## Interactions

### View Category
1. Click category card
2. View settings
3. Configure options
4. Save changes

### View Changes
1. View recent changes
2. Check old/new values
3. Review who changed
4. Understand impact

### Search Settings
1. Type query
2. Search settings
3. View results
4. Navigate to setting

### Check Health
1. View health score
2. Review issues
3. Read recommendations
4. Take action

## Responsive Breakpoints

| Breakpoint | Layout |
|------------|--------|
| Desktop (>1024px) | Full grid + changes |
| Tablet (768-1024px) | Stacked grid |
| Mobile (<768px) | Simplified list |

## Loading States
- Categories: Skeleton grid
- Changes: Skeleton cards
- Health: Loading score

## Error States
- Load failure: Retry button
- Save failure: Toast error
- Network error: Toast notification

## Accessibility
- Categories are focusable
- Changes announced via `aria-live`
- Screen reader: "Category: General, 15 settings"
- Keyboard: Tab through categories

## Telemetry
- `settings_overview.view` — Screen loaded
- `settings_overview.category_view` — Category viewed
- `settings_overview.search` — Search performed
- `settings_overview.export` — Settings exported

## Implementation Notes
- Settings overview
- Change tracking
- Health monitoring
- AiDock provides settings suggestions
- Export for backup
