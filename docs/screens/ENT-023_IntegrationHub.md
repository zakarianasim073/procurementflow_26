# ENT-023: Integration Hub Screen Specification

**Module:** `features/integration-hub/IntegrationHubPage`
**Layer:** features
**Version:** 1.0.0
**Status:** Draft
**Workspace:** Settings

## Purpose
Manage third-party integrations, APIs, and webhooks.

## Screen Layout

```
┌─────────────────────────────────────────────────────────────┐
│ ExecutiveHeader                                             │
├──────────┬──────────────────────────────────────────────────┤
│          │ Breadcrumb: Settings > Integration Hub            │
│ Workspace├──────────────────────────────────────────────────┤
│   Nav    │ IntegrationHubHeader (integrations, active)      │
│          ├──────────────────────────────────────────────────┤
│          │ IntegrationHub (main content)                    │
│          │ ┌────────────────────────────────────────────┐   │
│          │ │ IntegrationGrid (integrations)              │   │
│          │ │ ┌──────┬──────┬──────┬──────┐              │   │
│          │ │ │e-GP  │Email │Slack │Custom│              │   │
│          │ │ │API   │SMTP  │API   │API   │              │   │
│          │ │ └──────┴──────┴──────┴──────┘              │   │
│          │ ├────────────────────────────────────────────┤   │
│          │ │ IntegrationDetails (selected)               │   │
│          │ └────────────────────────────────────────────┘   │
├──────────┴──────────────────────────────────────────────────┤
│ AiDock (integration insights)                               │
└─────────────────────────────────────────────────────────────┘
```

## Component Tree

```
IntegrationHubPage
├── ExecutiveHeader
├── Breadcrumb
├── IntegrationHubHeader
│   ├── KpiStrip (integration_count, active_count)
│   └── Button (Add Integration)
├── IntegrationHub
│   ├── IntegrationGrid
│   │   └── IntegrationCard × N
│   │       ├── icon
│   │       ├── name
│   │       ├── description
│   │       ├── status
│   │       └── Button (Configure)
│   ├── IntegrationDetails
│   │   ├── integration_info
│   │   ├── configuration
│   │   ├── credentials
│   │   └── test_connection
│   ├── WebhookList
│   │   └── WebhookCard × N
│   │       ├── url
│   │       ├── events
│   │       ├── status
│   │       └── actions (test, delete)
│   └── ActivityLog
│       └── ActivityEntry × N
│           ├── timestamp
│           ├── event
│           └── status
└── AiDock
    ├── AgentCard (Integration Agent)
    └── EvidencePanel (integration insights)
```

## Data Sources

### Integrations
```typescript
// API: GET /api/v1/admin/integrations
interface IntegrationList {
  integrations: Integration[];
  total_count: number;
  active_count: number;
}

interface Integration {
  integration_id: string;
  name: string;
  type: 'api' | 'webhook' | 'smtp' | 'custom';
  status: 'active' | 'inactive' | 'error';
  configuration: Record<string, any>;
  last_sync: string;
  created_at: string;
}
```

### React Query
```typescript
const { data: integrations } = useQuery({
  queryKey: ['admin', 'integrations'],
  queryFn: () => api.get('/api/v1/admin/integrations'),
});

const testIntegration = useMutation({
  mutationFn: (integrationId: string) => api.post(`/api/v1/admin/integrations/${integrationId}/test`),
  onSuccess: (data) => {
    if (data.success) {
      toast.success('Connection successful');
    } else {
      toast.error('Connection failed');
    }
  },
});

const saveIntegration = useMutation({
  mutationFn: (integration: SaveIntegrationRequest) => api.post('/api/v1/admin/integrations', integration),
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ['admin', 'integrations'] });
    toast.success('Integration saved');
  },
});
```

## Zustand Store
```typescript
// stores/integrationHubStore.ts
interface IntegrationHubState {
  selectedIntegration: string | null;
  setIntegration: (id: string | null) => void;
}
```

## Interactions

### View Integration
1. Click integration card
2. View details
3. Check status
4. Review configuration

### Configure Integration
1. Click Configure button
2. Edit settings
3. Update credentials
4. Save changes

### Test Connection
1. Click Test button
2. Execute test
3. View results
4. Update status

### Add Webhook
1. Click Add Webhook
2. Enter URL
3. Select events
4. Save webhook

## Responsive Breakpoints

| Breakpoint | Layout |
|------------|--------|
| Desktop (>1024px) | Full grid + details |
| Tablet (768-1024px) | Grid with modal details |
| Mobile (<768px) | Simplified grid |

## Loading States
- Integrations: Skeleton cards
- Details: Loading spinner
- Test: Loading indicator

## Error States
- Connection failure: Error details
- Save failure: Toast error
- Network error: Toast notification

## Accessibility
- Integrations are focusable
- Status announced via `aria-live`
- Screen reader: "Integration: e-GP API, active"
- Keyboard: Tab through integrations

## Telemetry
- `integration_hub.view` — Screen loaded
- `integration_hub.configure` — Integration configured
- `integration_hub.test` — Connection tested
- `integration_hub.webhook_add` — Webhook added

## Implementation Notes
- Multiple integration types
- Webhook management
- Connection testing
- AiDock provides integration insights
- Export for analysis
