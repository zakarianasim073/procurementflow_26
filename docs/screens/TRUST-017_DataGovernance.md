# TRUST-017: Data Governance Screen Specification

**Module:** `features/data-governance/DataGovernancePage`
**Layer:** features
**Version:** 1.0.0
**Status:** Draft
**Workspace:** Trust

## Purpose
Data governance policies, quality metrics, and compliance tracking.

## Screen Layout

```
┌─────────────────────────────────────────────────────────────┐
│ ExecutiveHeader                                             │
├──────────┬──────────────────────────────────────────────────┤
│          │ Breadcrumb: Trust > Data Governance               │
│ Workspace├──────────────────────────────────────────────────┤
│   Nav    │ DataGovernanceHeader (policies, quality)         │
│          ├──────────────────────────────────────────────────┤
│          │ DataGovernance (main content)                    │
│          │ ┌────────────────────────────────────────────┐   │
│          │ │ Tabs: [Policies] [Quality] [Compliance]    │   │
│          │ ├────────────────────────────────────────────┤   │
│          │ │ PoliciesTab (governance policies)           │   │
│          │ │ QualityTab (data quality metrics)           │   │
│          │ │ ComplianceTab (compliance status)           │   │
│          │ └────────────────────────────────────────────┘   │
├──────────┴──────────────────────────────────────────────────┤
│ AiDock (governance insights)                                │
└─────────────────────────────────────────────────────────────┘
```

## Component Tree

```
DataGovernancePage
├── ExecutiveHeader
├── Breadcrumb
├── DataGovernanceHeader
│   ├── KpiStrip (policy_count, quality_score, compliance_rate)
│   └── Button (New Policy)
├── DataGovernance
│   ├── Tabs
│   │   ├── PoliciesTab
│   │   │   └── PolicyList
│   │   │       └── PolicyCard × N
│   │   │           ├── name
│   │   │           ├── description
│   │   │           ├── status
│   │   │           ├── last_review
│   │   │           └── Button (View)
│   │   ├── QualityTab
│   │   │   └── QualityMetrics
│   │   │       ├── completeness
│   │   │       ├── accuracy
│   │   │       ├── consistency
│   │   │       ├── timeliness
│   │   │       └── QualityChart
│   │   └── ComplianceTab
│   │       └── ComplianceStatus
│   │           ├── ComplianceCheck × N
│   │           │   ├── name
│   │           │   ├── status
│   │           │   └── details
│   │           └── ComplianceChart
│   └── GovernanceReport
│       ├── summary
│       ├── findings
│       └── recommendations
└── AiDock
    ├── AgentCard (Governance Agent)
    └── EvidencePanel (governance insights)
```

## Data Sources

### Data Governance
```typescript
// API: GET /api/v1/trust/governance
interface DataGovernance {
  policies: Policy[];
  quality: QualityMetrics;
  compliance: ComplianceStatus[];
}

interface Policy {
  policy_id: string;
  name: string;
  description: string;
  status: 'active' | 'draft' | 'archived';
  last_review: string;
  next_review: string;
  owner: string;
}

interface QualityMetrics {
  completeness: number;
  accuracy: number;
  consistency: number;
  timeliness: number;
  overall_score: number;
}

interface ComplianceStatus {
  check_id: string;
  name: string;
  status: 'pass' | 'fail' | 'warning';
  details: string;
  last_checked: string;
}
```

### React Query
```typescript
const { data: governance } = useQuery({
  queryKey: ['trust', 'governance'],
  queryFn: () => api.get('/api/v1/trust/governance'),
});

const createPolicy = useMutation({
  mutationFn: (policy: CreatePolicyRequest) => api.post('/api/v1/trust/governance/policies', policy),
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ['trust', 'governance'] });
    toast.success('Policy created');
  },
});
```

## Zustand Store
```typescript
// stores/dataGovernanceStore.ts
interface DataGovernanceState {
  activeTab: string;
  setTab: (tab: string) => void;
}
```

## Interactions

### View Policies
1. Click Policies tab
2. View policy list
3. Select policy
4. View details

### Check Quality
1. Click Quality tab
2. View metrics
3. Analyze charts
4. Read insights

### Review Compliance
1. Click Compliance tab
2. View checks
3. Address failures
4. Update status

### Create Policy
1. Click New Policy
2. Fill details
3. Set rules
4. Save policy

## Responsive Breakpoints

| Breakpoint | Layout |
|------------|--------|
| Desktop (>1024px) | Full tabs + panels |
| Tablet (768-1024px) | Stacked tabs |
| Mobile (<768px) | Simplified view |

## Loading States
- Policies: Skeleton cards
- Quality: Loading metrics
- Compliance: Loading checks

## Error States
- Load failure: Retry button
- Save failure: Toast error
- Network error: Toast notification

## Accessibility
- Policies are focusable
- Metrics announced via `aria-live`
- Screen reader: "Quality score: 85%"
- Keyboard: Tab through items

## Telemetry
- `data_governance.view` — Screen loaded
- `data_governance.policy_create` — Policy created
- `data_governance.quality_check` — Quality checked
- `data_governance.compliance_review` — Compliance reviewed

## Implementation Notes
- Policy management
- Quality metrics tracking
- Compliance monitoring
- AiDock provides governance insights
- Audit trail
