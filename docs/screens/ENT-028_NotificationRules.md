# ENT-028: Notification Rules Screen Specification

**Module:** `features/notification-rules/NotificationRulesPage`
**Layer:** features
**Version:** 1.0.0
**Status:** Draft
**Workspace:** Settings

## Purpose
Configure notification rules, triggers, and delivery channels.

## Screen Layout

```
┌─────────────────────────────────────────────────────────────┐
│ ExecutiveHeader                                             │
├──────────┬──────────────────────────────────────────────────┤
│          │ Breadcrumb: Settings > Notification Rules         │
│ Workspace├──────────────────────────────────────────────────┤
│   Nav    │ NotificationRulesHeader (rules, active)          │
│          ├──────────────────────────────────────────────────┤
│          │ NotificationRules (main content)                 │
│          │ ┌────────────────────────────────────────────┐   │
│          │ │ RuleList (notification rules)               │   │
│          │ │ ┌──────────────────────────────────────────┐│   │
│          │ │ │ Rule: New Tender Alert    [Active]       ││   │
│          │ │ │ Rule: Deadline Reminder   [Active]       ││   │
│          │ │ │ ...                                      ││   │
│          │ │ └──────────────────────────────────────────┘│   │
│          │ ├────────────────────────────────────────────┤   │
│          │ │ RuleDetails (selected rule)                 │   │
│          │ └────────────────────────────────────────────┘   │
├──────────┴──────────────────────────────────────────────────┤
│ AiDock (notification insights)                              │
└─────────────────────────────────────────────────────────────┘
```

## Component Tree

```
NotificationRulesPage
├── ExecutiveHeader
├── Breadcrumb
├── NotificationRulesHeader
│   ├── KpiStrip (rule_count, active_count)
│   └── Button (Create Rule)
├── NotificationRules
│   ├── RuleList
│   │   └── RuleCard × N
│   │       ├── name
│   │       ├── trigger
│   │       ├── channels
│   │       ├── status
│   │       └── actions (edit, toggle, delete)
│   ├── RuleDetails
│   │   ├── rule_info
│   │   ├── trigger_config
│   │   ├── conditions
│   │   ├── channels
│   │   └── Button (Test Rule)
│   ├── CreateRuleForm
│   │   ├── name
│   │   ├── trigger_type
│   │   ├── conditions
│   │   ├── channels
│   │   └── Button (Save Rule)
│   └── RuleStats
│       ├── chart (notifications_sent)
│       ├── chart (by_trigger)
│       └── chart (delivery_rate)
└── AiDock
    ├── AgentCard (Notification Agent)
    └── EvidencePanel (notification insights)
```

## Data Sources

### Notification Rules
```typescript
// API: GET /api/v1/admin/notification-rules
interface NotificationRuleList {
  rules: NotificationRule[];
  total_count: number;
  active_count: number;
}

interface NotificationRule {
  rule_id: string;
  name: string;
  description: string;
  trigger: TriggerConfig;
  conditions: Condition[];
  channels: string[];
  enabled: boolean;
  created_at: string;
  last_triggered?: string;
}

interface TriggerConfig {
  type: string;
  event: string;
  schedule?: string;
}

interface Condition {
  field: string;
  operator: string;
  value: any;
}
```

### React Query
```typescript
const { data: rules } = useQuery({
  queryKey: ['admin', 'notification-rules'],
  queryFn: () => api.get('/api/v1/admin/notification-rules'),
});

const createRule = useMutation({
  mutationFn: (rule: CreateRuleRequest) => api.post('/api/v1/admin/notification-rules', rule),
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ['admin', 'notification-rules'] });
    toast.success('Rule created');
  },
});

const toggleRule = useMutation({
  mutationFn: ({ ruleId, enabled }: { ruleId: string; enabled: boolean }) =>
    api.patch(`/api/v1/admin/notification-rules/${ruleId}`, { enabled }),
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ['admin', 'notification-rules'] });
    toast.success('Rule updated');
  },
});
```

## Zustand Store
```typescript
// stores/notificationRulesStore.ts
interface NotificationRulesState {
  selectedRule: string | null;
  setRule: (id: string | null) => void;
}
```

## Interactions

### View Rule
1. Click rule card
2. View details
3. Check trigger
4. Review channels

### Create Rule
1. Click Create
2. Fill form
3. Set conditions
4. Save rule

### Toggle Rule
1. Click toggle
2. Update status
3. Confirm change
4. Refresh list

### Test Rule
1. Click Test Rule
2. Execute test
3. View results
4. Confirm delivery

## Responsive Breakpoints

| Breakpoint | Layout |
|------------|--------|
| Desktop (>1024px) | Full list + details |
| Tablet (768-1024px) | List with modal details |
| Mobile (<768px) | Simplified list |

## Loading States
- Rules: Skeleton cards
- Details: Loading spinner
- Test: Loading indicator

## Error States
- Create failure: Toast error
- Toggle failure: Toast error
- Network error: Toast notification

## Accessibility
- Rules are focusable
- Status announced via `aria-live`
- Screen reader: "Rule: New Tender Alert, active"
- Keyboard: Tab through rules

## Telemetry
- `notification_rules.view` — Screen loaded
- `notification_rules.create` — Rule created
- `notification_rules.toggle` — Rule toggled
- `notification_rules.test` — Rule tested

## Implementation Notes
- Rule management
- Trigger configuration
- Multi-channel delivery
- AiDock provides notification insights
- Test functionality
