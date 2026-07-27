# TRUST-006: Compliance Monitor Screen Specification

**Module:** `features/compliance-monitor/ComplianceMonitorPage`
**Layer:** features
**Version:** 1.0.0
**Status:** Draft
**Workspace:** Trust

## Purpose
Regulatory compliance monitoring, PPR2025 adherence, and compliance reporting.

## Screen Layout

```
┌─────────────────────────────────────────────────────────────┐
│ ExecutiveHeader                                             │
├──────────┬──────────────────────────────────────────────────┤
│          │ Breadcrumb: Trust > Compliance Monitor            │
│ Workspace├──────────────────────────────────────────────────┤
│   Nav    │ ComplianceMonitorHeader (score, status)          │
│          ├──────────────────────────────────────────────────┤
│          │ ComplianceMonitor (main content)                 │
│          │ ┌────────────────────────────────────────────┐   │
│          │ │ ComplianceScore (overall gauge)             │   │
│          │ ├────────────────────────────────────────────┤   │
│          │ │ Tabs: [Rules] [Violations] [Reports]       │   │
│          │ ├────────────────────────────────────────────┤   │
│          │ │ ComplianceRules (rule cards)                │   │
│          │ │ ViolationLog (violations table)             │   │
│          │ │ ComplianceReports (generated reports)       │   │
│          │ └────────────────────────────────────────────┘   │
├──────────┴──────────────────────────────────────────────────┤
│ AiDock (compliance insights, fix suggestions)               │
└─────────────────────────────────────────────────────────────┘
```

## Component Tree

```
ComplianceMonitorPage
├── ExecutiveHeader
├── Breadcrumb
├── ComplianceMonitorHeader
│   ├── Gauge (compliance_score)
│   ├── Badge (status: compliant/non_compliant)
│   └── Button (Run Audit)
├── ComplianceMonitor
│   ├── ComplianceScore
│   │   └── Gauge (overall_score)
│   ├── Tabs
│   │   ├── RulesTab
│   │   │   └── ComplianceRules
│   │   │       └── RuleCard × N
│   │   │           ├── name
│   │   │           ├── description
│   │   │           ├── status (pass/fail)
│   │   │           └── last_checked
│   │   ├── ViolationsTab
│   │   │   └── ViolationLog
│   │   │       └── Table<Violation>
│   │   │           ├── timestamp
│   │   │           ├── rule
│   │   │           ├── severity
│   │   │           └── resolution
│   │   └── ReportsTab
│   │       └── ComplianceReports
│   │           └── Table<Report>
│   │               ├── name
│   │               ├── generated_at
│   │               ├── status
│   │               └── Button (Download)
│   └── AuditRunner
│       ├── Progress (audit progress)
│       └── Results (audit results)
└── AiDock
    ├── AgentCard (Compliance Agent)
    └── EvidencePanel (compliance insights)
```

## Data Sources

### Compliance Score
```typescript
// API: GET /api/v1/admin/compliance/score
interface ComplianceScore {
  overall_score: number;
  total_rules: number;
  passed_rules: number;
  failed_rules: number;
  status: 'compliant' | 'non_compliant';
  last_check: string;
}
```

### Compliance Rules
```typescript
// API: GET /api/v1/admin/compliance/rules
interface ComplianceRuleList {
  rules: ComplianceRule[];
}

interface ComplianceRule {
  rule_id: string;
  name: string;
  description: string;
  category: string;
  status: 'pass' | 'fail' | 'warning';
  last_checked: string;
  violations: number;
}
```

### Violations
```typescript
// API: GET /api/v1/admin/compliance/violations
interface ViolationList {
  violations: Violation[];
  total_count: number;
}

interface Violation {
  violation_id: string;
  timestamp: string;
  rule_id: string;
  rule_name: string;
  severity: 'critical' | 'high' | 'medium' | 'low';
  description: string;
  resolution?: string;
  resolved_at?: string;
}
```

### React Query
```typescript
const { data: score } = useQuery({
  queryKey: ['admin', 'compliance', 'score'],
  queryFn: () => api.get('/api/v1/admin/compliance/score'),
  refetchInterval: 60_000, // 1 minute
});

const { data: rules } = useQuery({
  queryKey: ['admin', 'compliance', 'rules'],
  queryFn: () => api.get('/api/v1/admin/compliance/rules'),
});

const { data: violations } = useQuery({
  queryKey: ['admin', 'compliance', 'violations', filters],
  queryFn: () => api.get('/api/v1/admin/compliance/violations', { params: filters }),
});

const runAudit = useMutation({
  mutationFn: () => api.post('/api/v1/admin/compliance/audit'),
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ['admin', 'compliance'] });
    toast.success('Audit completed');
  },
});
```

## Zustand Store
```typescript
// stores/complianceMonitorStore.ts
interface ComplianceMonitorState {
  activeTab: string;
  autoRefresh: boolean;
  setTab: (tab: string) => void;
  setAutoRefresh: (enabled: boolean) => void;
}
```

## Interactions

### Run Audit
1. Click "Run Audit"
2. Show progress
3. Update score
4. Show results

### View Violations
1. Click Violations tab
2. Filter by severity
3. Click violation for details
4. Resolve violation

### Download Report
1. Click Download button
2. Choose format
3. Include all details
4. Download file

### View Rules
1. Click Rules tab
2. View rule status
3. Analyze violations
4. Update rules

## Responsive Breakpoints

| Breakpoint | Layout |
|------------|--------|
| Desktop (>1024px) | Full tabs with tables |
| Tablet (768-1024px) | Stacked tabs |
| Mobile (<768px) | Single tab view |

## Loading States
- Score: Skeleton gauge
- Rules: Skeleton cards
- Violations: Skeleton table
- Reports: Skeleton table

## Error States
- Audit failure: Error details
- Load failure: Retry button
- Network error: Toast notification

## Accessibility
- Score announced via `aria-live`
- Violations are focusable
- Screen reader: "Compliance score: 85%"
- Keyboard: Enter to view details

## Telemetry
- `compliance_monitor.view` — Screen loaded
- `compliance_monitor.audit` — Audit run
- `compliance_monitor.violation_view` — Violation viewed
- `compliance_monitor.report` — Report downloaded

## Implementation Notes
- Compliance score gauge
- Rule management with status
- Violation tracking and resolution
- AiDock provides compliance insights
- Report generation and download
