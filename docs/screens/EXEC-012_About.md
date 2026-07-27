# EXEC-012: About Screen Specification

**Module:** `features/about/AboutPage`
**Layer:** features
**Version:** 1.0.0
**Status:** Draft
**Workspace:** Dashboard

## Purpose
System information, version details, and credits.

## Screen Layout

```
┌─────────────────────────────────────────────────────────────┐
│ ExecutiveHeader                                             │
├──────────┬──────────────────────────────────────────────────┤
│          │ Breadcrumb: Dashboard > About                     │
│ Workspace├──────────────────────────────────────────────────┤
│   Nav    │ AboutHeader (logo, version)                      │
│          ├──────────────────────────────────────────────────┤
│          │ About (main content)                             │
│          │ ┌────────────────────────────────────────────┐   │
│          │ │ Logo (ProcureFlow)                         │   │
│          │ ├────────────────────────────────────────────┤   │
│          │ │ SystemInfo (version, build, environment)   │   │
│          │ ├────────────────────────────────────────────┤   │
│          │ │ Tabs: [Info] [Credits] [License] [Links]   │   │
│          │ ├────────────────────────────────────────────┤   │
│          │ │ SystemDetails (detailed info)              │   │
│          │ │ CreditsList (contributors)                 │   │
│          │ │ LicenseInfo (open source)                  │   │
│          │ │ UsefulLinks (resources)                    │   │
│          │ └────────────────────────────────────────────┘   │
├──────────┴──────────────────────────────────────────────────┤
│ AiDock (system insights, recommendations)                   │
└─────────────────────────────────────────────────────────────┘
```

## Component Tree

```
AboutPage
├── ExecutiveHeader
├── Breadcrumb
├── AboutHeader
│   ├── Logo (large)
│   ├── KpiCard (app_name)
│   ├── KpiCard (version)
│   └── KpiCard (environment)
├── About
│   ├── Logo
│   │   └── Image (ProcureFlow logo)
│   ├── SystemInfo
│   │   ├── KpiCard (version)
│   │   ├── KpiCard (build)
│   │   ├── KpiCard (environment)
│   │   └── KpiCard (last_updated)
│   ├── Tabs
│   │   ├── InfoTab
│   │   │   └── SystemDetails
│   │   │       ├── Table<SystemInfo>
│   │   │       │   ├── key
│   │   │       │   └── value
│   │   │       └── Button (Copy Info)
│   │   ├── CreditsTab
│   │   │   └── CreditsList
│   │   │       └── CreditCard × N
│   │   │           ├── avatar
│   │   │           ├── name
│   │   │           ├── role
│   │   │           └── contribution
│   │   ├── LicenseTab
│   │   │   └── LicenseInfo
│   │   │       ├── license_name
│   │   │       ├── license_text
│   │   │       └── Button (View Full)
│   │   └── LinksTab
│   │       └── UsefulLinks
│   │           └── LinkCard × N
│   │               ├── icon
│   │               ├── title
│   │               ├── description
│   │               └── Button (Visit)
│   └── SystemActions
│       ├── Button (Check Updates)
│       ├── Button (View Changelog)
│       └── Button (Report Issue)
└── AiDock
    ├── AgentCard (System Agent)
    └── EvidencePanel (system insights)
```

## Data Sources

### System Info
```typescript
// API: GET /api/v1/admin/system/info
interface SystemInfo {
  app_name: string;
  version: string;
  build: string;
  environment: string;
  last_updated: string;
  node_version: string;
  python_version: string;
  database_version: string;
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
// stores/aboutStore.ts
interface AboutState {
  activeTab: string;
  setTab: (tab: string) => void;
}
```

## Interactions

### View System Info
1. Click Info tab
2. View system details
3. Copy info
4. Share details

### View Credits
1. Click Credits tab
2. View contributors
3. Read contributions
4. Visit profiles

### View License
1. Click License tab
2. Read license info
3. View full license
4. Understand terms

### Visit Links
1. Click Links tab
2. View resources
3. Click link
4. Open in new tab

## Responsive Breakpoints

| Breakpoint | Layout |
|------------|--------|
| Desktop (>1024px) | Full tabs with content |
| Tablet (768-1024px) | Stacked tabs |
| Mobile (<768px) | Single tab view |

## Loading States
- System info: Skeleton cards
- Credits: Skeleton cards
- License: Skeleton content

## Error States
- Load failure: Retry button
- Update check failure: Toast error
- Network error: Toast notification

## Accessibility
- Cards are focusable
- Info announced via `aria-live`
- Screen reader: "Version 1.0.0"
- Keyboard: Tab through elements

## Telemetry
- `about.view` — Screen loaded
- `about.tab_switch` — Tab changed
- `about.copy_info` — Info copied
- `about.check_updates` — Updates checked

## Implementation Notes
- System information display
- Credits for contributors
- License information
- Useful links and resources
- AiDock provides system insights
