# TRUST-013: Alert Center Screen Specification

**Module:** `features/alerts/AlertCenterPage`
**Layer:** features
**Version:** 1.0.0
**Status:** Draft
**Workspace:** Trust

## Purpose
System alert management, notification routing, and escalation.

## Screen Layout

```
┌─────────────────────────────────────────────────────────────┐
│ ExecutiveHeader                                             │
├──────────┬──────────────────────────────────────────────────┤
│          │ Breadcrumb: Trust > Alert Center                  │
│ Workspace├──────────────────────────────────────────────────┤
│   Nav    │ AlertCenterHeader (active alerts, severity)      │
│          ├──────────────────────────────────────────────────┤
│          │ AlertCenter (main content)                       │
│          │ ┌────────────────────────────────────────────┐   │
│          │ │ AlertBanner (critical alerts)               │   │
│          │ ├────────────────────────────────────────────┤   │
│          │ │ Tabs: [Active] [History] [Rules] [Settings]│   │
│          │ ├────────────────────────────────────────────┤   │
│          │ │ ActiveAlerts (current alerts)               │   │
│          │ │ AlertHistory (past alerts)                  │   │
│          │ │ AlertRules (notification rules)             │   │
│          │ │ AlertSettings (configuration)               │   │
│          │ └────────────────────────────────────────────┘   │
├──────────┴──────────────────────────────────────────────────┤
│ AiDock (alert insights, escalation)                         │
└─────────────────────────────────────────────────────────────┘
```

## Component Tree

```
AlertCenterPage
├── ExecutiveHeader
├── Breadcrumb
├── AlertCenterHeader
│   ├── Badge (active_count)
│   ├── Badge (critical_count)
│   └── Button (Mute All)
├── AlertCenter
│   ├── AlertBanner
│   │   └── AlertCard × N (critical)
│   │       ├── severity
│   │       ├── title
│   │       ├── message
│   │       └── Button (Acknowledge)
│   ├── Tabs
│   │   ├── ActiveTab
│   │   │   └── ActiveAlerts
│   │   │       └── AlertCard × N
│   │   │           ├── severity
│   │   │           ├── title
│   │   │           ├── message
│   │   │           ├── timestamp
│   │   │           ├── source
│   │   │           └── actions (acknowledge, snooze, dismiss)
│   │   ├── HistoryTab
│   │   │   └── AlertHistory
│   │   │       └── Table<Alert>
│   │   │           ├── timestamp
│   │   │           ├── severity
│   │   │           ├── title
│   │   │           ├── status
│   │   │           └── Button (View)
│   │   ├── RulesTab
│   │   │   └── AlertRules
│   │   │       └── Table<AlertRule>
│   │   │           ├── name
│   │   │           ├── condition
│   │   │           ├── notification
│   │   │           └── actions (edit, delete)
│   │   └── SettingsTab
│   │       └── AlertSettings
│   │           ├── Switch (email_notifications)
│   │           ├── Switch (push_notifications)
│   │           ├── Input (mute_duration)
│   │           └── Button (Save)
│   └── AlertDetail
│       ├── alert_info
│       ├── timeline
│       └── actions (resolve, escalate)
└── AiDock
    ├── AgentCard (Monitoring Agent)
    └── EvidencePanel (alert insights)
```

## Data Sources

### Alerts
```typescript
// API: GET /api/v1/admin/alerts
interface AlertList {
  alerts: Alert[];
  active_count: number;
  critical_count: number;
}

interface Alert {
  alert_id: string;
  severity: 'info' | 'warning' | 'critical';
  title: string;
  message: string;
  source: string;
  status: 'active' | 'acknowledged' | 'resolved' | 'dismissed';
  created_at: string;
  acknowledged_at?: string;
  resolved_at?: string;
  metadata?: Record<string, any>;
}
```

### Alert Rules
```typescript
// API: GET /api/v1/admin/alerts/rules
interface AlertRuleList {
  rules: AlertRule[];
}

interface AlertRule {
  rule_id: string;
  name: string;
  condition: string;
  severity: string;
  notification: 'email' | 'push' | 'sms';
  enabled: boolean;
}
```

### React Query
```typescript
const { data: alerts } = useQuery({
  queryKey: ['admin', 'alerts'],
  queryFn: () => api.get('/api/v1/admin/alerts'),
  refetchInterval: 30_000, // 30 seconds
});

const { data: rules } = useQuery({
  queryKey: ['admin', 'alerts', 'rules'],
  queryFn: () => api.get('/api/v1/admin/alerts/rules'),
});

const acknowledgeAlert = useMutation({
  mutationFn: (alertId: string) => api.post(`/api/v1/admin/alerts/${alertId}/acknowledge`),
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ['admin', 'alerts'] });
    toast.success('Alert acknowledged');
  },
});

const resolveAlert = useMutation({
  mutationFn: (alertId: string) => api.post(`/api/v1/admin/alerts/${alertId}/resolve`),
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ['admin', 'alerts'] });
    toast.success('Alert resolved');
  },
});
```

## Zustand Store
```typescript
// stores/alertCenterStore.ts
interface AlertCenterState {
  activeTab: string;
  selectedAlert: string | null;
  setTab: (tab: string) => void;
  setAlert: (id: string | null) => void;
}
```

## Interactions

### View Alert
1. Click alert card
2. Open AlertDetail
3. View timeline
4. Take action

### Acknowledge Alert
1. Click Acknowledge button
2. Confirm acknowledgment
3. Update status
4. Remove from active

### Resolve Alert
1. Click Resolve button
2. Enter resolution
3. Submit resolution
4. Update status

### Manage Rules
1. Click Rules tab
2. View rule list
3. Edit rule
4. Save changes

## Responsive Breakpoints

| Breakpoint | Layout |
|------------|--------|
| Desktop (>1024px) | Full tabs with cards |
| Tablet (768-1024px) | Stacked tabs |
| Mobile (<768px) | Single tab view |

## Loading States
- Alerts: Skeleton cards
- Rules: Skeleton table
- Settings: Skeleton form

## Error States
- Acknowledge failure: Toast error
- Resolve failure: Toast error
- Network error: Toast notification

## Accessibility
- Alert cards are focusable
- Severity announced via `aria-live`
- Screen reader: "Critical alert: System overload"
- Keyboard: Enter to acknowledge, Tab to navigate

## Telemetry
- `alert_center.view` — Screen loaded
- `alert_center.acknowledge` — Alert acknowledged
- `alert_center.resolve` — Alert resolved
- `alert_center.rule_edit` — Rule edited

## Implementation Notes
- Real-time alert monitoring
- Severity-based prioritization
- Rule-based notifications
- AiDock provides alert insights
- Export for audit trail
