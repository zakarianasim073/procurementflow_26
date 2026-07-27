# ENT-014: Integration Management Screen Specification

**Module:** `features/integrations/IntegrationManagementPage`
**Layer:** features
**Version:** 1.0.0
**Status:** Draft
**Workspace:** Settings

## Purpose
Third-party integration management, API connections, and sync configuration.

## Screen Layout

```
┌─────────────────────────────────────────────────────────────┐
│ ExecutiveHeader                                             │
├──────────┬──────────────────────────────────────────────────┤
│          │ Breadcrumb: Settings > Integration Management     │
│ Workspace├──────────────────────────────────────────────────┤
│   Nav    │ IntegrationManagementHeader (count, status)      │
│          ├──────────────────────────────────────────────────┤
│          │ IntegrationManagement (main content)             │
│          │ ┌────────────────────────────────────────────┐   │
│          │ │ Tabs: [Available] [Connected] [Settings]   │   │
│          │ ├────────────────────────────────────────────┤   │
│          │ │ AvailableIntegrations (integration cards)   │   │
│          │ │ ConnectedIntegrations (active connections)  │   │
│          │ │ IntegrationSettings (global config)         │   │
│          │ └────────────────────────────────────────────┘   │
├──────────┴──────────────────────────────────────────────────┤
│ AiDock (integration insights, recommendations)              │
└─────────────────────────────────────────────────────────────┘
```

## Component Tree

```
IntegrationManagementPage
├── ExecutiveHeader
├── Breadcrumb
├── IntegrationManagementHeader
│   ├── KpiStrip (integration_count, active_count, sync_count)
│   └── Button (Add Integration)
├── IntegrationManagement
│   ├── Tabs
│   │   ├── AvailableTab
│   │   │   └── AvailableIntegrations
│   │   │       └── IntegrationCard × N
│   │   │           ├── icon
│   │   │           ├── name
│   │   │           ├── description
│   │   │           ├── category
│   │   │           └── Button (Connect)
│   │   ├── ConnectedTab
│   │   │   └── ConnectedIntegrations
│   │   │       └── IntegrationCard × N
│   │   │           ├── icon
│   │   │           ├── name
│   │   │           ├── status
│   │   │           ├── last_sync
│   │   │           └── actions (configure, sync, disconnect)
│   │   └── SettingsTab
│   │       └── IntegrationSettings
│   │           ├── Input (sync_frequency)
│   │           ├── Switch (auto_sync)
│   │           ├── Switch (error_notifications)
│   │           └── Button (Save)
│   └── IntegrationDetail
│       ├── configuration
│       ├── sync_status
│       └── error_log
└── AiDock
    ├── AgentCard (Integration Agent)
    └── EvidencePanel (integration insights)
```

## Data Sources

### Integrations
```typescript
// API: GET /api/v1/admin/integrations
interface IntegrationList {
  available: Integration[];
  connected: ConnectedIntegration[];
}

interface Integration {
  integration_id: string;
  name: string;
  description: string;
  icon: string;
  category: string;
  configured: boolean;
}

interface ConnectedIntegration {
  connection_id: string;
  integration_id: string;
  name: string;
  status: 'active' | 'error' | 'syncing';
  last_sync?: string;
  sync_count: number;
  error_count: number;
}
```

### React Query
```typescript
const { data: integrations } = useQuery({
  queryKey: ['admin', 'integrations'],
  queryFn: () => api.get('/api/v1/admin/integrations'),
});

const connectIntegration = useMutation({
  mutationFn: (request: ConnectRequest) => api.post('/api/v1/admin/integrations/connect', request),
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ['admin', 'integrations'] });
    toast.success('Integration connected');
  },
});

const syncIntegration = useMutation({
  mutationFn: (connectionId: string) => api.post(`/api/v1/admin/integrations/${connectionId}/sync`),
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ['admin', 'integrations'] });
    toast.success('Sync started');
  },
});

const disconnectIntegration = useMutation({
  mutationFn: (connectionId: string) => api.delete(`/api/v1/admin/integrations/${connectionId}`),
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ['admin', 'integrations'] });
    toast.success('Integration disconnected');
  },
});
```

## Zustand Store
```typescript
// stores/integrationManagementStore.ts
interface IntegrationManagementState {
  activeTab: string;
  selectedIntegration: string | null;
  setTab: (tab: string) => void;
  setIntegration: (id: string | null) => void;
}
```

## Interactions

### Connect Integration
1. Click Connect button
2. Configure credentials
3. Test connection
4. Save configuration

### Sync Integration
1. Click Sync button
2. Start sync process
3. Monitor progress
4. View results

### Configure Integration
1. Click Configure button
2. Edit settings
3. Save changes
4. Update status

### Disconnect Integration
1. Click Disconnect button
2. Confirm disconnection
3. Remove connection
4. Update list

## Responsive Breakpoints

| Breakpoint | Layout |
|------------|--------|
| Desktop (>1024px) | Full tabs with cards |
| Tablet (768-1024px) | Stacked tabs |
| Mobile (<768px) | Single tab view |

## Loading States
- Integrations: Skeleton cards
- Sync: Progress indicator
- Settings: Skeleton form

## Error States
- Connection failure: Error details
- Sync failure: Error log
- Network error: Toast notification

## Accessibility
- Integration cards are focusable
- Status announced via `aria-live`
- Screen reader: "Integration X, active"
- Keyboard: Enter to select, Tab to navigate

## Telemetry
- `integration_management.view` — Screen loaded
- `integration_management.connect` — Integration connected
- `integration_management.sync` — Sync triggered
- `integration_management.disconnect` — Integration disconnected

## Implementation Notes
- Available integrations catalog
- Connected integrations management
- Sync configuration
- AiDock provides integration insights
- Export for audit trail
