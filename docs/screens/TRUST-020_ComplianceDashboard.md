# TRUST-020: Compliance Dashboard Screen Specification

**Module:** `features/compliance-dashboard/ComplianceDashboardPage`
**Layer:** features
**Version:** 1.0.0
**Status:** Draft
**Workspace:** Trust

## Purpose
Monitor compliance status, policies, and regulatory requirements.

## Screen Layout

```
┌─────────────────────────────────────────────────────────────┐
│ ExecutiveHeader                                             │
├──────────┬──────────────────────────────────────────────────┤
│          │ Breadcrumb: Trust > Compliance Dashboard          │
│ Workspace├──────────────────────────────────────────────────┤
│   Nav    │ ComplianceDashboardHeader (score, violations)    │
│          ├──────────────────────────────────────────────────┤
│          │ ComplianceDashboard (main content)               │
│          │ ┌────────────────────────────────────────────┐   │
│          │ │ ComplianceScore (overall score)             │   │
│          │ ├────────────────────────────────────────────┤   │
│          │ │ Tabs: [Overview] [Policies] [Violations]    │   │
│          │ ├────────────────────────────────────────────┤   │
│          │ │ OverviewTab (summary charts)                │   │
│          │ │ PoliciesTab (compliance policies)           │   │
│          │ │ ViolationsTab (violations log)              │   │
│          │ └────────────────────────────────────────────┘   │
├──────────┴──────────────────────────────────────────────────┤
│ AiDock (compliance insights)                                │
└─────────────────────────────────────────────────────────────┘
```

## Component Tree

```
ComplianceDashboardPage
├── ExecutiveHeader
├── Breadcrumb
├── ComplianceDashboardHeader
│   ├── KpiStrip (compliance_score, violations_count, policies_count)
│   └── Button (Run Compliance Check)
├── ComplianceDashboard
│   ├── ComplianceScore
│   │   ├── score_gauge
│   │   ├── score_history
│   │   └── score_breakdown
│   ├── Tabs
│   │   ├── OverviewTab
│   │   │   ├── Chart (compliance_trend)
│   │   │   ├── Chart (violations_by_category)
│   │   │   └── Chart (policy_coverage)
│   │   ├── PoliciesTab
│   │   │   └── PolicyList
│   │   │       └── PolicyCard × N
│   │   │           ├── name
│   │   │           ├── status
│   │   │           ├── last_check
│   │   │           └── Button (Review)
│   │   └── ViolationsTab
│   │       └── ViolationList
│   │           └── ViolationCard × N
│   │               ├── type
│   │               ├── severity
│   │               ├── description
│   │               └── Button (Remediate)
│   └── ComplianceReport
│       ├── summary
│       ├── findings
│       └── recommendations
└── AiDock
    ├── AgentCard (Compliance Agent)
    └── EvidencePanel (compliance insights)
```

## Data Sources

### Compliance Data
```typescript
// API: GET /api/v1/trust/compliance
interface ComplianceData {
  score: number;
  policies: Policy[];
  violations: Violation[];
  report: ComplianceReport;
}

interface Policy {
  policy_id: string;
  name: string;
  description: string;
  status: 'compliant' | 'non_compliant' | 'warning';
  last_check: string;
  next_check: string;
}

interface Violation {
  violation_id: string;
  type: string;
  severity: 'low' | 'medium' | 'high' | 'critical';
  description: string;
  policy_id: string;
  detected_at: string;
  status: 'open' | 'in_progress' | 'resolved';
}

interface ComplianceReport {
  generated_at: string;
  summary: string;
  findings: string[];
  recommendations: string[];
}
```

### React Query
```typescript
const { data: compliance } = useQuery({
  queryKey: ['trust', 'compliance'],
  queryFn: () => api.get('/api/v1/trust/compliance'),
});

const runCheck = useMutation({
  mutationFn: () => api.post('/api/v1/trust/compliance/check'),
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ['trust', 'compliance'] });
    toast.success('Compliance check completed');
  },
});

const remediate = useMutation({
  mutationFn: (violationId: string) => api.post(`/api/v1/trust/compliance/remediate/${violationId}`),
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ['trust', 'compliance'] });
    toast.success('Remediation started');
  },
});
```

## Zustand Store
```typescript
// stores/complianceDashboardStore.ts
interface ComplianceDashboardState {
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

### View Policies
1. Click Policies tab
2. View policy list
3. Check status
4. Review details

### Review Violations
1. Click Violations tab
2. View violations
3. Check severity
4. Start remediation

### Generate Report
1. Click Generate Report
2. Compile findings
3. Create recommendations
4. Export report

## Responsive Breakpoints

| Breakpoint | Layout |
|------------|--------|
| Desktop (>1024px) | Full tabs + panels |
| Tablet (768-1024px) | Stacked tabs |
| Mobile (<768px) | Simplified view |

## Loading States
- Compliance: Loading score
- Policies: Skeleton cards
- Violations: Loading list

## Error States
- Check failure: Retry button
- Remediation failure: Error details
- Network error: Toast notification

## Accessibility
- Policies are focusable
- Score announced via `aria-live`
- Screen reader: "Compliance score: 92%"
- Keyboard: Tab through policies

## Telemetry
- `compliance_dashboard.view` — Screen loaded
- `compliance_dashboard.check` — Check run
- `compliance_dashboard.remediate` — Remediation started
- `compliance_dashboard.report` — Report generated

## Implementation Notes
- Compliance monitoring
- Policy management
- Violation tracking
- AiDock provides compliance insights
- Report generation
