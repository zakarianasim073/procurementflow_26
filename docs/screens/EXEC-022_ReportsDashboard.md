# EXEC-022: Reports Dashboard Screen Specification

**Module:** `features/reports-dashboard/ReportsDashboardPage`
**Layer:** features
**Version:** 1.0.0
**Status:** Draft
**Workspace:** Dashboard

## Purpose
Centralized report management, scheduling, and distribution.

## Screen Layout

```
┌─────────────────────────────────────────────────────────────┐
│ ExecutiveHeader                                             │
├──────────┬──────────────────────────────────────────────────┤
│          │ Breadcrumb: Dashboard > Reports Dashboard         │
│ Workspace├──────────────────────────────────────────────────┤
│   Nav    │ ReportsDashboardHeader (reports, scheduled)      │
│          ├──────────────────────────────────────────────────┤
│          │ ReportsDashboard (main content)                  │
│          │ ┌────────────────────────────────────────────┐   │
│          │ │ Tabs: [Recent] [Scheduled] [Templates]      │   │
│          │ ├────────────────────────────────────────────┤   │
│          │ │ RecentTab (recent reports)                  │   │
│          │ │ ScheduledTab (scheduled reports)            │   │
│          │ │ TemplatesTab (report templates)             │   │
│          │ └────────────────────────────────────────────┘   │
├──────────┴──────────────────────────────────────────────────┤
│ AiDock (report suggestions)                                 │
└─────────────────────────────────────────────────────────────┘
```

## Component Tree

```
ReportsDashboardPage
├── ExecutiveHeader
├── Breadcrumb
├── ReportsDashboardHeader
│   ├── KpiStrip (report_count, scheduled_count)
│   └── Button (Create Report)
├── ReportsDashboard
│   ├── Tabs
│   │   ├── RecentTab
│   │   │   └── ReportList
│   │   │       └── ReportCard × N
│   │   │           ├── name
│   │   │           ├── type
│   │   │           ├── generated_at
│   │   │           ├── status
│   │   │           └── actions (download, share, delete)
│   │   ├── ScheduledTab
│   │   │   └── ScheduleList
│   │   │       └── ScheduleCard × N
│   │   │           ├── name
│   │   │           ├── frequency
│   │   │           ├── next_run
│   │   │           ├── recipients
│   │   │           └── actions (edit, disable, run_now)
│   │   └── TemplatesTab
│   │       └── TemplateList
│   │           └── TemplateCard × N
│   │               ├── name
│   │               ├── description
│   │               ├── category
│   │               └── Button (Use Template)
│   ├── ReportStats
│   │   ├── chart (reports_over_time)
│   │   ├── chart (by_type)
│   │   └── chart (by_category)
│   └── QuickReports
│       └── QuickReport × N
│           ├── name
│           ├── description
│           └── Button (Generate)
└── AiDock
    ├── AgentCard (Report Agent)
    └── EvidencePanel (report suggestions)
```

## Data Sources

### Reports
```typescript
// API: GET /api/v1/reports/dashboard
interface ReportsDashboard {
  reports: Report[];
  scheduled: ScheduledReport[];
  templates: ReportTemplate[];
}

interface Report {
  report_id: string;
  name: string;
  type: string;
  category: string;
  generated_at: string;
  status: 'generated' | 'pending' | 'failed';
  file_url?: string;
  file_size?: number;
}

interface ScheduledReport {
  schedule_id: string;
  name: string;
  template_id: string;
  frequency: 'daily' | 'weekly' | 'monthly';
  next_run: string;
  recipients: string[];
  enabled: boolean;
}

interface ReportTemplate {
  template_id: string;
  name: string;
  description: string;
  category: string;
  parameters: Parameter[];
}

interface Parameter {
  name: string;
  type: string;
  required: boolean;
  default?: any;
}
```

### React Query
```typescript
const { data: dashboard } = useQuery({
  queryKey: ['reports', 'dashboard'],
  queryFn: () => api.get('/api/v1/reports/dashboard'),
});

const generateReport = useMutation({
  mutationFn: (request: GenerateReportRequest) => api.post('/api/v1/reports/generate', request),
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ['reports', 'dashboard'] });
    toast.success('Report generated');
  },
});

const scheduleReport = useMutation({
  mutationFn: (schedule: ScheduleReportRequest) => api.post('/api/v1/reports/schedule', schedule),
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ['reports', 'dashboard'] });
    toast.success('Report scheduled');
  },
});
```

## Zustand Store
```typescript
// stores/reportsDashboardStore.ts
interface ReportsDashboardState {
  activeTab: string;
  setTab: (tab: string) => void;
}
```

## Interactions

### View Recent
1. Click Recent tab
2. View report list
3. Check status
4. Download report

### Manage Scheduled
1. Click Scheduled tab
2. View schedules
3. Edit settings
4. Run now

### Use Template
1. Click Templates tab
2. View templates
3. Select template
4. Generate report

### Create Report
1. Click Create Report
2. Select template
3. Configure parameters
4. Generate report

## Responsive Breakpoints

| Breakpoint | Layout |
|------------|--------|
| Desktop (>1024px) | Full tabs + cards |
| Tablet (768-1024px) | Stacked tabs |
| Mobile (<768px) | Simplified list |

## Loading States
- Reports: Skeleton cards
- Schedules: Loading list
- Templates: Loading cards

## Error States
- Generate failure: Toast error
- Schedule failure: Toast error
- Network error: Toast notification

## Accessibility
- Reports are focusable
- Status announced via `aria-live`
- Screen reader: "Report: Monthly Summary, generated"
- Keyboard: Tab through reports

## Telemetry
- `reports_dashboard.view` — Screen loaded
- `reports_dashboard.generate` — Report generated
- `reports_dashboard.schedule` — Report scheduled
- `reports_dashboard.download` — Report downloaded

## Implementation Notes
- Report management
- Scheduling system
- Template gallery
- AiDock provides report suggestions
- Export functionality
