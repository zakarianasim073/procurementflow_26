# TRUST-014: Notification Rules Screen Specification

**Module:** `features/notification-rules/NotificationRulesPage`
**Layer:** features
**Version:** 1.0.0
**Status:** Draft
**Workspace:** Trust

## Purpose
Configure notification rules, escalation policies, and alert routing.

## Screen Layout

```
┌─────────────────────────────────────────────────────────────┐
│ ExecutiveHeader                                             │
├──────────┬──────────────────────────────────────────────────┤
│          │ Breadcrumb: Trust > Notification Rules            │
│ Workspace├──────────────────────────────────────────────────┤
│   Nav    │ NotificationRulesHeader (count, active)          │
│          ├──────────────────────────────────────────────────┤
│          │ NotificationRules (main content)                 │
│          │ ┌────────────────────────────────────────────┐   │
│          │ │ Tabs: [Rules] [Escalation] [Channels]      │   │
│          │ ├────────────────────────────────────────────┤   │
│          │ │ RuleList (notification rules)               │   │
│          │ │ EscalationPolicies (escalation config)      │   │
│          │ │ ChannelSettings (notification channels)     │   │
│          │ └────────────────────────────────────────────┘   │
├──────────┴──────────────────────────────────────────────────┤
│ AiDock (rule insights, optimization)                        │
└─────────────────────────────────────────────────────────────┘
```

## Component Tree

```
NotificationRulesPage
├── ExecutiveHeader
├── Breadcrumb
├── NotificationRulesHeader
│   ├── KpiStrip (rule_count, active_count, triggered_today)
│   └── Button (Add Rule)
├── NotificationRules
│   ├── Tabs
│   │   ├── RulesTab
│   │   │   └── RuleList
│   │   │       └── RuleCard × N
│   │   │           ├── name
│   │   │           ├── condition
│   │   │           ├── action
│   │   │           ├── status
│   │   │           └── actions (edit, test, delete)
│   │   ├── EscalationTab
│   │   │   └── EscalationPolicies
│   │   │       └── PolicyCard × N
│   │   │           ├── name
│   │   │           ├── levels
│   │   │           ├── timeout
│   │   │           └── Button (Edit)
│   │   └── ChannelsTab
│   │       └── ChannelSettings
│   │           ├── ChannelCard × N
│   │           │   ├── type (email, push, sms)
│   │           │   ├── status
│   │           │   └── Button (Configure)
│   │           └── Button (Add Channel)
│   └── RuleDetail
│       ├── condition_editor
│       ├── action_config
│       └── test_results
└── AiDock
    ├── AgentCard (Notification Agent)
    └── EvidencePanel (rule insights)
```

## Data Sources

### Notification Rules
```typescript
// API: GET /api/v1/admin/notifications/rules
interface RuleList {
  rules: NotificationRule[];
  total_count: number;
}

interface NotificationRule {
  rule_id: string;
  name: string;
  condition: string;
  action: string;
  channel: string;
  status: 'active' | 'inactive';
  triggered_count: number;
  last_triggered?: string;
  created_at: string;
}
```

### Escalation Policies
```typescript
// API: GET /api/v1/admin/notifications/escalation
interface EscalationPolicyList {
  policies: EscalationPolicy[];
}

interface EscalationPolicy {
  policy_id: string;
  name: string;
  levels: EscalationLevel[];
  timeout: number;
  enabled: boolean;
}

interface EscalationLevel {
  level: number;
  recipients: string[];
  delay: number;
}
```

### React Query
```typescript
const { data: rules } = useQuery({
  queryKey: ['admin', 'notifications', 'rules'],
  queryFn: () => api.get('/api/v1/admin/notifications/rules'),
});

const { data: policies } = useQuery({
  queryKey: ['admin', 'notifications', 'escalation'],
  queryFn: () => api.get('/api/v1/admin/notifications/escalation'),
});

const addRule = useMutation({
  mutationFn: (request: AddRuleRequest) => api.post('/api/v1/admin/notifications/rules', request),
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ['admin', 'notifications'] });
    toast.success('Rule added');
  },
});

const testRule = useMutation({
  mutationFn: (ruleId: string) => api.post(`/api/v1/admin/notifications/rules/${ruleId}/test`),
  onSuccess: () => {
    toast.success('Test notification sent');
  },
});
```

## Zustand Store
```typescript
// stores/notificationRulesStore.ts
interface NotificationRulesState {
  activeTab: string;
  selectedRule: string | null;
  setTab: (tab: string) => void;
  setRule: (id: string | null) => void;
}
```

## Interactions

### View Rules
1. Click Rules tab
2. View rule list
3. Check status
4. Manage rules

### Edit Rule
1. Click Edit button
2. Modify condition/action
3. Save changes
4. Update status

### Test Rule
1. Click Test button
2. Send test notification
3. View results
4. Verify delivery

### Configure Escalation
1. Click Escalation tab
2. View policy list
3. Edit levels
4. Save configuration

## Responsive Breakpoints

| Breakpoint | Layout |
|------------|--------|
| Desktop (>1024px) | Full tabs with cards |
| Tablet (768-1024px) | Stacked tabs |
| Mobile (<768px) | Single tab view |

## Loading States
- Rules: Skeleton cards
- Escalation: Skeleton cards
- Channels: Skeleton cards

## Error States
- Add failure: Toast error
- Test failure: Toast error
- Network error: Toast notification

## Accessibility
- Rule cards are focusable
- Status announced via `aria-live`
- Screen reader: "Rule X, active"
- Keyboard: Enter to edit, Tab to navigate

## Telemetry
- `notification_rules.view` — Screen loaded
- `notification_rules.add` — Rule added
- `notification_rules.test` — Rule tested
- `notification_rules.delete` — Rule deleted

## Implementation Notes
- Rule management with CRUD
- Escalation policy configuration
- Channel settings
- AiDock provides rule insights
- Export for audit trail
