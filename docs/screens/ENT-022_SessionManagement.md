# ENT-022: Session Management Screen Specification

**Module:** `features/session-management/SessionManagementPage`
**Layer:** features
**Version:** 1.0.0
**Status:** Draft
**Workspace:** Settings

## Purpose
Manage user sessions, active connections, and security controls.

## Screen Layout

```
┌─────────────────────────────────────────────────────────────┐
│ ExecutiveHeader                                             │
├──────────┬──────────────────────────────────────────────────┤
│          │ Breadcrumb: Settings > Session Management         │
│ Workspace├──────────────────────────────────────────────────┤
│   Nav    │ SessionManagementHeader (sessions, active)       │
│          ├──────────────────────────────────────────────────┤
│          │ SessionManagement (main content)                 │
│          │ ┌────────────────────────────────────────────┐   │
│          │ │ SessionList (active sessions)               │   │
│          │ │ ┌──────────────────────────────────────────┐│   │
│          │ │ │ Session: User A - Chrome - 10:00         ││   │
│          │ │ │ Session: User B - Firefox - 10:05        ││   │
│          │ │ │ ...                                      ││   │
│          │ │ └──────────────────────────────────────────┘│   │
│          │ ├────────────────────────────────────────────┤   │
│          │ │ SessionDetails (selected session)           │   │
│          │ └────────────────────────────────────────────┘   │
├──────────┴──────────────────────────────────────────────────┤
│ AiDock (session insights)                                   │
└─────────────────────────────────────────────────────────────┘
```

## Component Tree

```
SessionManagementPage
├── ExecutiveHeader
├── Breadcrumb
├── SessionManagementHeader
│   ├── KpiStrip (total_sessions, active_sessions)
│   └── Button (Terminate All)
├── SessionManagement
│   ├── SessionList
│   │   └── SessionCard × N
│   │       ├── user
│   │       ├── browser
│   │       ├── ip_address
│   │       ├── last_activity
│   │       └── actions (view, terminate)
│   ├── SessionDetails
│   │   ├── user_info
│   │   ├── session_info
│   │   ├── activity_log
│   │   └── security_info
│   ├── SessionHistory
│   │   └── HistoryEntry × N
│   │       ├── timestamp
│   │       ├── action
│   │       └── details
│   └── SecuritySettings
│       ├── session_timeout
│       ├── max_concurrent
│       └── ip_whitelist
└── AiDock
    ├── AgentCard (Security Agent)
    └── EvidencePanel (session insights)
```

## Data Sources

### Sessions
```typescript
// API: GET /api/v1/admin/sessions
interface SessionList {
  sessions: Session[];
  total_count: number;
  active_count: number;
}

interface Session {
  session_id: string;
  user_id: string;
  user_name: string;
  browser: string;
  ip_address: string;
  last_activity: string;
  created_at: string;
  status: 'active' | 'expired' | 'terminated';
}
```

### React Query
```typescript
const { data: sessions } = useQuery({
  queryKey: ['admin', 'sessions'],
  queryFn: () => api.get('/api/v1/admin/sessions'),
  refetchInterval: 30_000,
});

const terminateSession = useMutation({
  mutationFn: (sessionId: string) => api.delete(`/api/v1/admin/sessions/${sessionId}`),
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ['admin', 'sessions'] });
    toast.success('Session terminated');
  },
});

const terminateAll = useMutation({
  mutationFn: () => api.post('/api/v1/admin/sessions/terminate-all'),
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ['admin', 'sessions'] });
    toast.success('All sessions terminated');
  },
});
```

## Zustand Store
```typescript
// stores/sessionManagementStore.ts
interface SessionManagementState {
  selectedSession: string | null;
  setSession: (id: string | null) => void;
}
```

## Interactions

### View Session
1. Click session card
2. View details
3. Check activity
4. Review security

### Terminate Session
1. Click Terminate button
2. Confirm termination
3. Remove session
4. Update list

### Terminate All
1. Click Terminate All
2. Confirm action
3. Remove all sessions
4. Update count

### Update Settings
1. Click Settings
2. Modify timeout
3. Set limits
4. Save changes

## Responsive Breakpoints

| Breakpoint | Layout |
|------------|--------|
| Desktop (>1024px) | Full list + details |
| Tablet (768-1024px) | List with modal details |
| Mobile (<768px) | Simplified list |

## Loading States
- Sessions: Skeleton cards
- Details: Loading spinner
- Terminate: Loading state

## Error States
- Load failure: Retry button
- Terminate failure: Toast error
- Network error: Toast notification

## Accessibility
- Sessions are focusable
- Status announced via `aria-live`
- Screen reader: "Session: User A, active"
- Keyboard: Tab through sessions

## Telemetry
- `session_management.view` — Screen loaded
- `session_management.terminate` — Session terminated
- `session_management.terminate_all` — All terminated
- `session_management.settings_change` — Settings changed

## Implementation Notes
- Real-time session monitoring
- Security controls
- Activity logging
- AiDock provides session insights
- Export for audit
