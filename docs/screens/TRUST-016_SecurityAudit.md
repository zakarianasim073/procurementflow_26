# TRUST-016: Security Audit Screen Specification

**Module:** `features/security-audit/SecurityAuditPage`
**Layer:** features
**Version:** 1.0.0
**Status:** Draft
**Workspace:** Trust

## Purpose
Security audit logs, compliance checks, and vulnerability assessments.

## Screen Layout

```
┌─────────────────────────────────────────────────────────────┐
│ ExecutiveHeader                                             │
├──────────┬──────────────────────────────────────────────────┤
│          │ Breadcrumb: Trust > Security Audit                │
│ Workspace├──────────────────────────────────────────────────┤
│   Nav    │ SecurityAuditHeader (score, findings)            │
│          ├──────────────────────────────────────────────────┤
│          │ SecurityAudit (main content)                     │
│          │ ┌────────────────────────────────────────────┐   │
│          │ │ SecurityScore (overall score)               │   │
│          │ ├────────────────────────────────────────────┤   │
│          │ │ Tabs: [Findings] [Compliance] [History]     │   │
│          │ ├────────────────────────────────────────────┤   │
│          │ │ FindingsList (security findings)            │   │
│          │ │ ComplianceStatus (compliance checks)        │   │
│          │ │ AuditHistory (audit history)                │   │
│          │ └────────────────────────────────────────────┘   │
├──────────┴──────────────────────────────────────────────────┤
│ AiDock (security insights)                                  │
└─────────────────────────────────────────────────────────────┘
```

## Component Tree

```
SecurityAuditPage
├── ExecutiveHeader
├── Breadcrumb
├── SecurityAuditHeader
│   ├── KpiStrip (security_score, findings_count, critical_count)
│   └── Button (Run Audit)
├── SecurityAudit
│   ├── SecurityScore
│   │   ├── score_gauge
│   │   ├── score_history
│   │   └── score_breakdown
│   ├── Tabs
│   │   ├── FindingsTab
│   │   │   └── FindingsList
│   │   │       └── FindingCard × N
│   │   │           ├── severity
│   │   │           ├── title
│   │   │           ├── description
│   │   │           └── Button (Remediate)
│   │   ├── ComplianceTab
│   │   │   └── ComplianceStatus
│   │   │       ├── ComplianceCheck × N
│   │   │       │   ├── name
│   │   │       │   ├── status
│   │   │       │   └── details
│   │   │       └── ComplianceChart
│   │   └── HistoryTab
│   │       └── AuditHistory
│   │           └── AuditEntry × N
│   │               ├── date
│   │               ├── score
│   │               └── findings
│   └── RemediationPlan
│       └── RemediationItem × N
│           ├── finding
│           ├── priority
│           ├── status
│           └── due_date
└── AiDock
    ├── AgentCard (Security Agent)
    └── EvidencePanel (security insights)
```

## Data Sources

### Security Audit
```typescript
// API: GET /api/v1/trust/security/audit
interface SecurityAudit {
  score: number;
  findings: SecurityFinding[];
  compliance: ComplianceStatus[];
  history: AuditEntry[];
}

interface SecurityFinding {
  finding_id: string;
  severity: 'low' | 'medium' | 'high' | 'critical';
  title: string;
  description: string;
  recommendation: string;
  status: 'open' | 'in_progress' | 'resolved';
  created_at: string;
}

interface ComplianceStatus {
  check_id: string;
  name: string;
  status: 'pass' | 'fail' | 'warning';
  details: string;
  last_checked: string;
}

interface AuditEntry {
  audit_id: string;
  date: string;
  score: number;
  findings_count: number;
  duration: number;
}
```

### React Query
```typescript
const { data: audit } = useQuery({
  queryKey: ['trust', 'security', 'audit'],
  queryFn: () => api.get('/api/v1/trust/security/audit'),
});

const runAudit = useMutation({
  mutationFn: () => api.post('/api/v1/trust/security/audit/run'),
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ['trust', 'security', 'audit'] });
    toast.success('Audit completed');
  },
});

const remediate = useMutation({
  mutationFn: (findingId: string) => api.post(`/api/v1/trust/security/audit/remediate/${findingId}`),
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ['trust', 'security', 'audit'] });
    toast.success('Remediation started');
  },
});
```

## Zustand Store
```typescript
// stores/securityAuditStore.ts
interface SecurityAuditState {
  activeTab: string;
  setTab: (tab: string) => void;
}
```

## Interactions

### Run Audit
1. Click Run Audit button
2. Execute audit
3. Display results
4. Update score

### View Finding
1. Click finding card
2. View details
3. Read recommendation
4. Start remediation

### Check Compliance
1. Click Compliance tab
2. View checks
3. Review status
4. Address failures

### View History
1. Click History tab
2. View audit entries
3. Track score changes
4. Analyze trends

## Responsive Breakpoints

| Breakpoint | Layout |
|------------|--------|
| Desktop (>1024px) | Full tabs + details |
| Tablet (768-1024px) | Stacked tabs |
| Mobile (<768px) | Simplified view |

## Loading States
- Audit: Loading animation
- Findings: Skeleton cards
- Compliance: Loading checks

## Error States
- Audit failure: Retry button
- Remediation failure: Error details
- Network error: Toast notification

## Accessibility
- Findings are focusable
- Score announced via `aria-live`
- Screen reader: "Security score: 85/100"
- Keyboard: Tab through findings

## Telemetry
- `security_audit.view` — Screen loaded
- `security_audit.run` — Audit run
- `security_audit.remediate` — Remediation started
- `security_audit.compliance_check` — Compliance checked

## Implementation Notes
- Automated security scanning
- Compliance checking
- Remediation tracking
- AiDock provides security insights
- Audit history
