# ENT-011: API Keys Screen Specification

**Module:** `features/api-keys/ApiKeysPage`
**Layer:** features
**Version:** 1.0.0
**Status:** Draft
**Workspace:** Settings

## Purpose
API key management, usage tracking, and access control.

## Screen Layout

```
┌─────────────────────────────────────────────────────────────┐
│ ExecutiveHeader                                             │
├──────────┬──────────────────────────────────────────────────┤
│          │ Breadcrumb: Settings > API Keys                   │
│ Workspace├──────────────────────────────────────────────────┤
│   Nav    │ ApiKeysHeader (key count, usage)                 │
│          ├──────────────────────────────────────────────────┤
│          │ ApiKeys (main content)                           │
│          │ ┌────────────────────────────────────────────┐   │
│          │ │ Tabs: [Keys] [Usage] [Settings]            │   │
│          │ ├────────────────────────────────────────────┤   │
│          │ │ KeyList (API key cards)                     │   │
│          │ │ UsageChart (API usage analytics)            │   │
│          │ │ SettingsForm (rate limits, quotas)          │   │
│          │ └────────────────────────────────────────────┘   │
├──────────┴──────────────────────────────────────────────────┤
│ AiDock (key insights, usage optimization)                   │
└─────────────────────────────────────────────────────────────┘
```

## Component Tree

```
ApiKeysPage
├── ExecutiveHeader
├── Breadcrumb
├── ApiKeysHeader
│   ├── KpiStrip (key_count, total_requests, avg_daily)
│   └── Button (Create Key)
├── ApiKeys
│   ├── Tabs
│   │   ├── KeysTab
│   │   │   └── KeyList
│   │   │       └── KeyCard × N
│   │   │           ├── name
│   │   │           ├── key_preview
│   │   │           ├── created_at
│   │   │           ├── last_used
│   │   │           ├── status
│   │   │           └── actions (revoke, edit)
│   │   ├── UsageTab
│   │   │   └── UsageChart
│   │   │       ├── Chart (requests_over_time)
│   │   │       ├── Chart (by_endpoint)
│   │   │       └── Table (usage_details)
│   │   └── SettingsTab
│   │       └── SettingsForm
│   │           ├── Input (rate_limit)
│   │           ├── Input (daily_quota)
│   │           ├── Switch (ip_whitelist)
│   │           └── Button (Save)
│   └── KeyDetail
│       ├── key_info
│       ├── usage_stats
│       └── permissions
└── AiDock
    ├── AgentCard (Admin Agent)
    └── EvidencePanel (key insights)
```

## Data Sources

### API Keys
```typescript
// API: GET /api/v1/admin/api-keys
interface ApiKeyList {
  keys: ApiKey[];
  total_count: number;
}

interface ApiKey {
  key_id: string;
  name: string;
  key_preview: string;
  created_at: string;
  last_used?: string;
  status: 'active' | 'revoked';
  permissions: string[];
  usage_stats: {
    total_requests: number;
    avg_daily: number;
  };
}
```

### Usage Analytics
```typescript
// API: GET /api/v1/admin/api-keys/usage
interface ApiUsage {
  total_requests: number;
  avg_daily: number;
  by_endpoint: Record<string, number>;
  over_time: { date: string; count: number }[];
}
```

### React Query
```typescript
const { data: keys } = useQuery({
  queryKey: ['admin', 'api-keys'],
  queryFn: () => api.get('/api/v1/admin/api-keys'),
});

const { data: usage } = useQuery({
  queryKey: ['admin', 'api-keys', 'usage'],
  queryFn: () => api.get('/api/v1/admin/api-keys/usage'),
});

const createKey = useMutation({
  mutationFn: (request: CreateKeyRequest) => api.post('/api/v1/admin/api-keys', request),
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ['admin', 'api-keys'] });
    toast.success('API key created');
  },
});

const revokeKey = useMutation({
  mutationFn: (keyId: string) => api.delete(`/api/v1/admin/api-keys/${keyId}`),
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ['admin', 'api-keys'] });
    toast.success('API key revoked');
  },
});
```

## Zustand Store
```typescript
// stores/apiKeysStore.ts
interface ApiKeysState {
  activeTab: string;
  selectedKey: string | null;
  setTab: (tab: string) => void;
  setKey: (id: string | null) => void;
}
```

## Interactions

### Create Key
1. Click "Create Key"
2. Enter name/permissions
3. Generate key
4. Show key (once only)

### Revoke Key
1. Click Revoke button
2. Confirm revocation
3. Revoke key
4. Update list

### View Usage
1. Click Usage tab
2. View charts
3. Analyze patterns
4. Export report

### Update Settings
1. Click Settings tab
2. Edit rate limits
3. Save changes
4. Apply settings

## Responsive Breakpoints

| Breakpoint | Layout |
|------------|--------|
| Desktop (>1024px) | Full tabs with cards |
| Tablet (768-1024px) | Stacked tabs |
| Mobile (<768px) | Single tab view |

## Loading States
- Keys: Skeleton cards
- Usage: Skeleton charts
- Settings: Skeleton form

## Error States
- Create failure: Toast error
- Revoke failure: Toast error
- Network error: Retry button

## Accessibility
- Key cards are focusable
- Status announced via `aria-live`
- Screen reader: "Key X, active"
- Keyboard: Enter to select, Tab to navigate

## Telemetry
- `api_keys.view` — Screen loaded
- `api_keys.create` — Key created
- `api_keys.revoke` — Key revoked
- `api_keys.usage_view` — Usage viewed

## Implementation Notes
- Key management with CRUD
- Usage analytics with charts
- Rate limiting configuration
- AiDock provides key insights
- Export for audit trail
