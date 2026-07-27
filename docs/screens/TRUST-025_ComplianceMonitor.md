# TRUST-025: Compliance Monitor Screen Specification

**Module:** `features/compliance-monitor/ComplianceMonitorPage`
**Layer:** features
**Version:** 1.0.0
**Status:** Draft
**Workspace:** Trust

## Purpose
Real-time compliance monitoring, violations tracking, and remediation.

## Screen Layout

```
┌─────────────────────────────────────────────────────────────┐
│ ExecutiveHeader                                             │
├──────────┬──────────────────────────────────────────────────┤
│          │ Breadcrumb: Trust > Compliance Monitor            │
│ Workspace├──────────────────────────────────────────────────┤
│   Nav    │ ComplianceMonitorHeader (score, violations)      │
│          ├──────────────────────────────────────────────────┤
│          │ ComplianceMonitor (main content)                 │
│          │ ┌────────────────────────────────────────────┐   │
│          │ │ ComplianceScore (overall score)             │   │
│          │ ├────────────────────────────────────────────┤   │
│          │ │ Tabs: [Violations] [Policies] [Remediation]│   │
│          │ ├────────────────────────────────────────────┤   │
│          │ │ ViolationsTab (active violations)           │   │
│          │ │ PoliciesTab (compliance policies)           │   │
│          │ │ RemediationTab (remediation tasks)          │   │
│          │ └────────────────────────────────────────────┘   │
├──────────┴──────────────────────────────────────────────────┤
│ AiDock (compliance insights)                                │
└─────────────────────────────────────────────────────────────┘
```

## Component Tree

```
ComplianceMonitorPage
├── ExecutiveHeader
├── Breadcrumb
├── ComplianceMonitorHeader
│   ├── KpiStrip (compliance_score, violations_count, remediation_count)
│   └── Button (Run Check)
├── ComplianceMonitor
│   ├── ComplianceScore
│   │   ├── score_gauge
│   │   ├── score_trend
│   │   └── score_breakdown
│   ├── Tabs
│   │   ├── ViolationsTab
│   │   │   └── ViolationList
│   │   │       └── ViolationCard × N
│   │   │           ├── type
│   │   │           ├── severity
│   │   │           ├── policy
│   │   │           ├── detected_at
│   │   │           └── Button (Remediate)
│   │   ├── PoliciesTab
│   │   │   └── PolicyList
│   │   │       └── PolicyCard × N
│   │   │           ├── name
│   │   │           ├── status
│   │   │           ├── last_check
│   │   │           └── Button (Review)
│   │   └── RemediationTab
│   │       └── RemediationList
│   │           └── RemediationCard × N
│   │               ├── violation
│   │               ├── status
│   │               ├── assignee
│   │               └── Button (Update)
│   └── ComplianceTimeline
│       └── TimelineEntry × N
│           ├── timestamp
│           ├── event
│           └── details
└── AiDock
    ├── AgentCard (Compliance Agent)
    └── EvidencePanel (compliance insights)
```

## Data Sources

### Compliance Monitor
```typescript
// API: GET /api/v1/trust/compliance/monitor
interface ComplianceMonitor {
  score: number;
  violations: Violation[];
  policies: Policy[];
  remediations: Remediation[];
}

interface Violation {
  violation_id: string;
  type: string;
  severity: 'low' | 'medium' | 'high' | 'critical';
  policy_id: string;
  policy_name: string;
  description: string;
  detected_at: string;
  status: 'open' | 'in_progress' | 'resolved';
}

interface Policy {
  policy_id: string;
  name: string;
  description: string;
  status: 'compliant' | 'non_compliant' | 'warning';
  last_check: string;
  violations_count: number;
}

interface Remediation {
  remediation_id: string;
  violation_id: string;
  description: string;
  status: 'pending' | 'in_progress' | 'completed';
  assignee: string;
  due_date: string;
}
```

### React Query
```typescript
const { data: monitor } = useQuery({
  queryKey: ['trust', 'compliance', 'monitor'],
  queryFn: () => api.get('/api/v1/trust/compliance/monitor'),
});

const runCheck = useMutation({
  mutationFn: () => api.post('/api/v1/trust/compliance/check'),
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ['trust', 'compliance', 'monitor'] });
    toast.success('Compliance check completed');
  },
});

const remediate = useMutation({
  mutationFn: (violationId: string) => api.post(`/api/v1/trust/compliance/remediate/${violationId}`),
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ['trust', 'compliance', 'monitor'] });
    toast.success('Remediation started');
  },
});
```

## Zustand Store
```typescript
// stores/complianceMonitorStore.ts
interface ComplianceMonitorState {
  activeTab: string;
  setTab: (tab: string) => void;
}
```

## Interactions

### Run Check
1. Click Run Check
2. Execute scan
3. Display results
4. Update score

### View Violations
1. Click Violations tab
2. View violation list
3. Check severity
4. Start remediation

### Review Policies
1. Click Policies tab
2. View policy list
3. Check status
4. Review violations

### Track Remediation
1. Click Remediation tab
2. View tasks
3. Update status
4. Complete task

## Responsive Breakpoints

| Breakpoint | Layout |
|------------|--------|
| Desktop (>1024px) | Full tabs + panels |
| Tablet (768-1024px) | Stacked tabs |
| Mobile (<768px) | Simplified view |

## Loading States
- Score: Loading gauge
- Violations: Loading list
- Policies: Loading cards

## Error States
- Check failure: Retry button
- Remediation failure: Error details
- Network error: Toast notification

## Accessibility
- Violations are focusable
- Score announced via `aria-live`
- Screen reader: "Compliance score: 85%"
- Keyboard: Tab through violations

## Telemetry
- `compliance_monitor.view` — Screen loaded
- `compliance_monitor.check` — Check run
- `compliance_monitor.remediate` — Remediation started

## Implementation Notes
- Real-time compliance monitoring
- Violation tracking
- Remediation management
- AiDock provides compliance insights
- Export for reporting
