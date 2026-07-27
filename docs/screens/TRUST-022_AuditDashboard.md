# TRUST-022: Audit Dashboard Screen Specification

**Module:** `features/audit-dashboard/AuditDashboardPage`
**Layer:** features
**Version:** 1.0.0
**Status:** Draft
**Workspace:** Trust

## Purpose
Comprehensive audit trail, compliance logging, and activity monitoring.

## Screen Layout

```
┌─────────────────────────────────────────────────────────────┐
│ ExecutiveHeader                                             │
├──────────┬──────────────────────────────────────────────────┤
│          │ Breadcrumb: Trust > Audit Dashboard               │
│ Workspace├──────────────────────────────────────────────────┤
│   Nav    │ AuditDashboardHeader (entries, compliance)       │
│          ├──────────────────────────────────────────────────┤
│          │ AuditDashboard (main content)                    │
│          │ ┌────────────────────────────────────────────┐   │
│          │ │ AuditStats (overview)                       │   │
│          │ ├────────────────────────────────────────────┤   │
│          │ │ Tabs: [Activity] [Compliance] [Reports]     │   │
│          │ ├────────────────────────────────────────────┤   │
│          │ │ ActivityTab (audit entries)                 │   │
│          │ │ ComplianceTab (compliance status)           │   │
│          │ │ ReportsTab (audit reports)                  │   │
│          │ └────────────────────────────────────────────┘   │
├──────────┴──────────────────────────────────────────────────┤
│ AiDock (audit insights)                                     │
└─────────────────────────────────────────────────────────────┘
```

## Component Tree

```
AuditDashboardPage
├── ExecutiveHeader
├── Breadcrumb
├── AuditDashboardHeader
│   ├── KpiStrip (entry_count, compliance_score, violations)
│   └── Button (Export Audit)
├── AuditDashboard
│   ├── AuditStats
│   │   ├── Chart (activity_trend)
│   │   ├── Chart (compliance_trend)
│   │   └── Chart (violations_by_type)
│   ├── Tabs
│   │   ├── ActivityTab
│   │   │   ├── FilterBar
│   │   │   │   ├── ChipSelect (action_type)
│   │   │   │   ├── ChipSelect (user)
│   │   │   │   └── CalendarRange (date_range)
│   │   │   └── ActivityList
│   │   │       └── ActivityCard × N
│   │   │           ├── user
│   │   │           ├── action
│   │   │           ├── target
│   │   │           ├── timestamp
│   │   │           └── details
│   │   ├── ComplianceTab
│   │   │   └── ComplianceList
│   │   │       └── ComplianceCard × N
│   │   │           ├── policy
│   │   │           ├── status
│   │   │           ├── last_check
│   │   │           └── Button (Review)
│   │   └── ReportsTab
│   │       └── ReportList
│   │           └── ReportCard × N
│   │               ├── name
│   │               ├── date
│   │               ├── status
│   │               └── Button (Download)
│   └── AuditTimeline
│       └── TimelineEntry × N
│           ├── timestamp
│           ├── event
│           └── user
└── AiDock
    ├── AgentCard (Audit Agent)
    └── EvidencePanel (audit insights)
```

## Data Sources

### Audit Data
```typescript
// API: GET /api/v1/trust/audit/dashboard
interface AuditData {
  entries: AuditEntry[];
  compliance: ComplianceStatus[];
  reports: AuditReport[];
  stats: AuditStats;
}

interface AuditEntry {
  entry_id: string;
  user_id: string;
  user_name: string;
  action: string;
  target: string;
  timestamp: string;
  details: Record<string, any>;
  ip_address: string;
}

interface ComplianceStatus {
  policy_id: string;
  policy_name: string;
  status: 'compliant' | 'non_compliant' | 'warning';
  last_check: string;
  next_check: string;
}

interface AuditReport {
  report_id: string;
  name: string;
  date: string;
  status: 'generated' | 'pending';
  file_url?: string;
}

interface AuditStats {
  total_entries: number;
  compliance_score: number;
  violations_count: number;
  active_users: number;
}
```

### React Query
```typescript
const { data: audit } = useQuery({
  queryKey: ['trust', 'audit', 'dashboard'],
  queryFn: () => api.get('/api/v1/trust/audit/dashboard'),
});

const { data: entries } = useQuery({
  queryKey: ['trust', 'audit', 'entries', filters],
  queryFn: () => api.get('/api/v1/trust/audit/entries', { params: filters }),
});

const generateReport = useMutation({
  mutationFn: (request: GenerateReportRequest) => api.post('/api/v1/trust/audit/reports', request),
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ['trust', 'audit', 'dashboard'] });
    toast.success('Report generated');
  },
});
```

## Zustand Store
```typescript
// stores/auditDashboardStore.ts
interface AuditDashboardState {
  activeTab: string;
  filters: {
    action_type: string[];
    user: string[];
    date_range: { start: string; end: string } | null;
  };
  setTab: (tab: string) => void;
  setFilter: <K extends keyof AuditDashboardState['filters']>(key: K, value: AuditDashboardState['filters'][K]) => void;
}
```

## Interactions

### View Activity
1. Click Activity tab
2. Apply filters
3. View entries
4. Check details

### Check Compliance
1. Click Compliance tab
2. View policies
3. Check status
4. Review violations

### Generate Report
1. Click Reports tab
2. Select report type
3. Configure options
4. Generate report

### Export Audit
1. Click Export
2. Choose format
3. Apply filters
4. Download file

## Responsive Breakpoints

| Breakpoint | Layout |
|------------|--------|
| Desktop (>1024px) | Full tabs + panels |
| Tablet (768-1024px) | Stacked tabs |
| Mobile (<768px) | Simplified view |

## Loading States
- Entries: Skeleton cards
- Compliance: Loading list
- Reports: Loading cards

## Error States
- Load failure: Retry button
- Generate failure: Toast error
- Network error: Toast notification

## Accessibility
- Entries are focusable
- Stats announced via `aria-live`
- Screen reader: "Audit entry: User A performed action"
- Keyboard: Tab through entries

## Telemetry
- `audit_dashboard.view` — Screen loaded
- `audit_dashboard.filter` — Filter applied
- `audit_dashboard.report_generate` — Report generated
- `audit_dashboard.export` — Audit exported

## Implementation Notes
- Comprehensive audit trail
- Compliance monitoring
- Report generation
- AiDock provides audit insights
- Export for compliance
