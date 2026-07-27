# ENT-013: Webhook Management Screen Specification

**Module:** `features/webhooks/WebhookManagementPage`
**Layer:** features
**Version:** 1.0.0
**Status:** Draft
**Workspace:** Settings

## Purpose
Webhook configuration, delivery monitoring, and integration management.

## Screen Layout

```
┌─────────────────────────────────────────────────────────────┐
│ ExecutiveHeader                                             │
├──────────┬──────────────────────────────────────────────────┤
│          │ Breadcrumb: Settings > Webhook Management         │
│ Workspace├──────────────────────────────────────────────────┤
│   Nav    │ WebhookManagementHeader (count, status)          │
│          ├──────────────────────────────────────────────────┤
│          │ WebhookManagement (main content)                 │
│          │ ┌────────────────────────────────────────────┐   │
│          │ │ Tabs: [Webhooks] [Logs] [Settings]         │   │
│          │ ├────────────────────────────────────────────┤   │
│          │ │ WebhookList (webhook cards)                 │   │
│          │ │ DeliveryLogs (delivery history)             │   │
│          │ │ SettingsForm (global settings)              │   │
│          │ └────────────────────────────────────────────┘   │
├──────────┴──────────────────────────────────────────────────┤
│ AiDock (webhook insights, integration suggestions)          │
└─────────────────────────────────────────────────────────────┘
```

## Component Tree

```
WebhookManagementPage
├── ExecutiveHeader
├── Breadcrumb
├── WebhookManagementHeader
│   ├── KpiStrip (webhook_count, success_rate, avg_latency)
│   └── Button (Add Webhook)
├── WebhookManagement
│   ├── Tabs
│   │   ├── WebhooksTab
│   │   │   └── WebhookList
│   │   │       └── WebhookCard × N
│   │   │           ├── name
│   │   │           ├── url
│   │   │           ├── events
│   │   │           ├── status
│   │   │           └── actions (edit, test, delete)
│   │   ├── LogsTab
│   │   │   └── DeliveryLogs
│   │   │       └── Table<DeliveryLog>
│   │   │           ├── timestamp
│   │   │           ├── webhook
│   │   │           ├── event
│   │   │           ├── status
│   │   │           └── response_code
│   │   └── SettingsTab
│   │       └── SettingsForm
│   │           ├── Input (timeout)
│   │           ├── Input (max_retries)
│   │           ├── Switch (enableLogging)
│   │           └── Button (Save)
│   └── WebhookDetail
│       ├── configuration
│       ├── delivery_stats
│       └── recent_deliveries
└── AiDock
    ├── AgentCard (Integration Agent)
    └── EvidencePanel (webhook insights)
```

## Data Sources

### Webhooks
```typescript
// API: GET /api/v1/admin/webhooks
interface WebhookList {
  webhooks: Webhook[];
  total_count: number;
}

interface Webhook {
  webhook_id: string;
  name: string;
  url: string;
  secret?: string;
  events: string[];
  status: 'active' | 'inactive';
  created_at: string;
  last_triggered?: string;
  success_rate: number;
  avg_latency: number;
}
```

### Delivery Logs
```typescript
// API: GET /api/v1/admin/webhooks/logs
interface DeliveryLogList {
  logs: DeliveryLog[];
  total_count: number;
}

interface DeliveryLog {
  log_id: string;
  webhook_id: string;
  webhook_name: string;
  event: string;
  status: 'success' | 'failed' | 'pending';
  request_payload?: string;
  response_code?: number;
  response_body?: string;
  latency: number;
  created_at: string;
}
```

### React Query
```typescript
const { data: webhooks } = useQuery({
  queryKey: ['admin', 'webhooks'],
  queryFn: () => api.get('/api/v1/admin/webhooks'),
});

const { data: logs } = useQuery({
  queryKey: ['admin', 'webhooks', 'logs', filters],
  queryFn: () => api.get('/api/v1/admin/webhooks/logs', { params: filters }),
});

const addWebhook = useMutation({
  mutationFn: (request: AddWebhookRequest) => api.post('/api/v1/admin/webhooks', request),
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ['admin', 'webhooks'] });
    toast.success('Webhook added');
  },
});

const testWebhook = useMutation({
  mutationFn: (webhookId: string) => api.post(`/api/v1/admin/webhooks/${webhookId}/test`),
  onSuccess: () => {
    toast.success('Test webhook sent');
  },
});
```

## Zustand Store
```typescript
// stores/webhookManagementStore.ts
interface WebhookManagementState {
  activeTab: string;
  selectedWebhook: string | null;
  setTab: (tab: string) => void;
  setWebhook: (id: string | null) => void;
}
```

## Interactions

### Add Webhook
1. Click "Add Webhook"
2. Fill form
3. Select events
4. Save webhook

### Test Webhook
1. Click Test button
2. Send test event
3. View response
4. Check logs

### View Logs
1. Click Logs tab
2. Filter by webhook/event
3. Click log for details
4. Analyze failures

### Edit Webhook
1. Click Edit button
2. Modify settings
3. Save changes
4. Update status

## Responsive Breakpoints

| Breakpoint | Layout |
|------------|--------|
| Desktop (>1024px) | Full tabs with cards |
| Tablet (768-1024px) | Stacked tabs |
| Mobile (<768px) | Single tab view |

## Loading States
- Webhooks: Skeleton cards
- Logs: Skeleton table
- Settings: Skeleton form

## Error States
- Add failure: Toast error
- Test failure: Error details
- Network error: Toast notification

## Accessibility
- Webhook cards are focusable
- Status announced via `aria-live`
- Screen reader: "Webhook X, active"
- Keyboard: Enter to select, Tab to navigate

## Telemetry
- `webhook_management.view` — Screen loaded
- `webhook_management.add` — Webhook added
- `webhook_management.test` — Webhook tested
- `webhook_management.delete` — Webhook deleted

## Implementation Notes
- Webhook management with CRUD
- Delivery log monitoring
- Test webhook functionality
- AiDock provides webhook insights
- Export for audit trail
