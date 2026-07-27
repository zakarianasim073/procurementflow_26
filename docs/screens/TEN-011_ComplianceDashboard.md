# TEN-011: Compliance Dashboard Screen Specification

**Module:** `features/compliance-dashboard/ComplianceDashboardPage`
**Layer:** features
**Version:** 1.0.0
**Status:** Draft
**Workspace:** Acquisition

## Purpose
Overview of compliance status across all tenders, with alerts and action items.

## Screen Layout

```
┌─────────────────────────────────────────────────────────────┐
│ ExecutiveHeader                                             │
├──────────┬──────────────────────────────────────────────────┤
│          │ Breadcrumb: Acquisition > Compliance Dashboard    │
│ Workspace├──────────────────────────────────────────────────┤
│   Nav    │ ComplianceDashboardHeader (stats, alerts)        │
│          ├──────────────────────────────────────────────────┤
│          │ ComplianceDashboard (main content)               │
│          │ ┌────────────────────────────────────────────┐   │
│          │ │ KpiStrip (compliance metrics)               │   │
│          │ ├────────────────────────────────────────────┤   │
│          │ │ AlertsPanel (critical issues)               │   │
│          │ ├────────────────────────────────────────────┤   │
│          │ │ Tabs: [Overview] [Tenders] [Issues] [Reports]│  │
│          │ ├────────────────────────────────────────────┤   │
│          │ │ ComplianceOverview (summary charts)         │   │
│          │ │ TenderComplianceList (tender table)         │   │
│          │ │ IssuesList (compliance issues)              │   │
│          │ │ ReportsList (compliance reports)            │   │
│          │ └────────────────────────────────────────────┘   │
├──────────┴──────────────────────────────────────────────────┤
│ AiDock (compliance insights, action recommendations)        │
└─────────────────────────────────────────────────────────────┘
```

## Component Tree

```
ComplianceDashboardPage
├── ExecutiveHeader
├── Breadcrumb
├── ComplianceDashboardHeader
│   ├── KpiStrip (total_tenders, compliant, non_compliant, pending)
│   └── Badge (critical_alerts)
├── ComplianceDashboard
│   ├── AlertsPanel
│   │   └── AlertCard × N
│   │       ├── severity
│   │       ├── title
│   │       ├── description
│   │       └── Button (Resolve)
│   ├── Tabs
│   │   ├── OverviewTab
│   │   │   └── ComplianceOverview
│   │   │       ├── Chart (compliance_trend)
│   │   │       ├── Chart (issues_by_type)
│   │   │       └── Gauge (overall_score)
│   │   ├── TendersTab
│   │   │   └── TenderComplianceList
│   │   │       └── Table<TenderCompliance>
│   │   │           ├── tender_id
│   │   │           ├── title
│   │   │           ├── status
│   │   │           ├── score
│   │   │           └── Button (View)
│   │   ├── IssuesTab
│   │   │   └── IssuesList
│   │   │       └── Table<ComplianceIssue>
│   │   │           ├── issue_type
│   │   │           ├── tender
│   │   │           ├── severity
│   │   │           └── Button (Fix)
│   │   └── ReportsTab
│   │       └── ReportsList
│   │           └── Table<ComplianceReport>
│   │               ├── name
│   │               ├── generated_at
│   │               └── Button (Download)
│   └── ComplianceSummary
│       ├── KpiCard (compliance_rate)
│       ├── KpiCard (avg_score)
│       └── KpiCard (open_issues)
└── AiDock
    ├── AgentCard (Compliance Agent)
    └── EvidencePanel (compliance insights)
```

## Data Sources

### Compliance Dashboard
```typescript
// API: GET /api/v1/boq/compliance/dashboard
interface ComplianceDashboard {
  stats: ComplianceStats;
  alerts: ComplianceAlert[];
  tenders: TenderCompliance[];
  issues: ComplianceIssue[];
  reports: ComplianceReport[];
}

interface ComplianceStats {
  total_tenders: number;
  compliant: number;
  non_compliant: number;
  pending: number;
  compliance_rate: number;
  avg_score: number;
  open_issues: number;
}

interface ComplianceAlert {
  alert_id: string;
  severity: 'critical' | 'high' | 'medium' | 'low';
  title: string;
  description: string;
  tender_id?: string;
  created_at: string;
}

interface TenderCompliance {
  tender_id: string;
  title: string;
  status: 'compliant' | 'non_compliant' | 'pending';
  score: number;
  last_checked: string;
  issues: number;
}

interface ComplianceIssue {
  issue_id: string;
  issue_type: string;
  tender_id: string;
  tender_title: string;
  severity: 'critical' | 'high' | 'medium' | 'low';
  description: string;
  status: 'open' | 'in_progress' | 'resolved';
}
```

### React Query
```typescript
const { data: dashboard } = useQuery({
  queryKey: ['boq', 'compliance', 'dashboard'],
  queryFn: () => api.get('/api/v1/boq/compliance/dashboard'),
  refetchInterval: 60_000, // 1 minute
});

const resolveIssue = useMutation({
  mutationFn: ({ issueId, resolution }: { issueId: string; resolution: string }) =>
    api.post(`/api/v1/boq/compliance/issues/${issueId}/resolve`, { resolution }),
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ['boq', 'compliance'] });
    toast.success('Issue resolved');
  },
});
```

## Zustand Store
```typescript
// stores/complianceDashboardStore.ts
interface ComplianceDashboardState {
  activeTab: string;
  selectedAlert: string | null;
  setTab: (tab: string) => void;
  setAlert: (id: string | null) => void;
}
```

## Interactions

### View Alert
1. Click alert card
2. Open AlertDrawer
3. View details
4. Take action

### Resolve Issue
1. Click "Fix" button
2. Enter resolution
3. Submit resolution
4. Update status

### View Tender Compliance
1. Click tender row
2. Open compliance detail
3. View score breakdown
4. Address issues

### Export Report
1. Click Download button
2. Choose format
3. Include all details
4. Download file

## Responsive Breakpoints

| Breakpoint | Layout |
|------------|--------|
| Desktop (>1024px) | Full dashboard with tabs |
| Tablet (768-1024px) | Stacked tabs |
| Mobile (<768px) | Single tab view |

## Loading States
- Stats: Skeleton cards
- Alerts: Skeleton cards
- Tables: Skeleton rows

## Error States
- Load failure: Retry button
- Resolution failure: Toast error
- Network error: Toast notification

## Accessibility
- Alerts are focusable
- Stats announced via `aria-live`
- Screen reader: "Compliance rate: 85%"
- Keyboard: Enter to view, Tab to navigate

## Telemetry
- `compliance_dashboard.view` — Screen loaded
- `compliance_dashboard.alert_click` — Alert viewed
- `compliance_dashboard.issue_resolve` — Issue resolved
- `compliance_dashboard.export` — Report exported

## Implementation Notes
- Real-time compliance monitoring
- Alerts panel for critical issues
- Tender compliance tracking
- AiDock provides compliance insights
- Export for reporting
