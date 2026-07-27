# EXEC-003: Reports Dashboard Screen Specification

**Module:** `features/reports/ReportsPage`
**Layer:** features
**Version:** 1.0.0
**Status:** Draft
**Workspace:** Dashboard

## Purpose
Report generation, template management, scheduled reports, and analytics export.

## Screen Layout

```
┌─────────────────────────────────────────────────────────────┐
│ ExecutiveHeader                                             │
├──────────┬──────────────────────────────────────────────────┤
│          │ Breadcrumb: Dashboard > Reports                   │
│ Workspace├──────────────────────────────────────────────────┤
│   Nav    │ ReportsHeader (templates, schedule)              │
│          ├──────────────────────────────────────────────────┤
│          │ ReportsDashboard (main content)                  │
│          │ ┌────────────────────────────────────────────┐   │
│          │ │ Tabs: [Generate] [Templates] [Scheduled]   │   │
│          │ ├────────────────────────────────────────────┤   │
│          │ │ ReportGenerator (form + preview)            │   │
│          │ │ TemplateLibrary (template cards)            │   │
│          │ │ ScheduledReports (cron jobs)                │   │
│          │ └────────────────────────────────────────────┘   │
├──────────┴──────────────────────────────────────────────────┤
│ AiDock (report suggestions, data insights)                  │
└─────────────────────────────────────────────────────────────┘
```

## Component Tree

```
ReportsPage
├── ExecutiveHeader
├── Breadcrumb
├── ReportsHeader
│   ├── KpiStrip (reports_count, scheduled, last_generated)
│   └── Button (Create Template)
├── ReportsDashboard
│   ├── Tabs
│   │   ├── GenerateTab
│   │   │   └── ReportGenerator
│   │   │       ├── Select (report_type)
│   │   │       ├── CalendarRange (date_range)
│   │   │       ├── ChipSelect (agencies)
│   │   │       ├── ChipSelect (zones)
│   │   │       ├── Select (format: PDF/Excel/CSV)
│   │   │       ├── Button (Generate)
│   │   │       └── ReportPreview
│   │   ├── TemplatesTab
│   │   │   └── TemplateLibrary
│   │   │       └── TemplateCard × N
│   │   │           ├── name
│   │   │           ├── description
│   │   │           ├── last_used
│   │   │           └── Button (Use Template)
│   │   └── ScheduledTab
│   │       └── ScheduledReports
│   │           └── Table<ScheduledReport>
│   │               ├── name
│   │               ├── frequency
│   │               ├── recipients
│   │               └── next_run
│   └── ReportHistory
│       └── Table<GeneratedReport>
│           ├── name
│           ├── generated_at
│           ├── format
│           └── Button (Download)
└── AiDock
    ├── AgentCard (Report Agent)
    └── EvidencePanel (report insights)
```

## Data Sources

### Report Templates
```typescript
// API: GET /api/v1/reports/templates
interface ReportTemplateList {
  templates: ReportTemplate[];
}

interface ReportTemplate {
  template_id: string;
  name: string;
  description: string;
  report_type: string;
  parameters: TemplateParameter[];
  last_used: string;
  use_count: number;
}

interface TemplateParameter {
  name: string;
  type: 'date' | 'select' | 'multiselect' | 'text';
  required: boolean;
  default?: any;
  options?: string[];
}
```

### Scheduled Reports
```typescript
// API: GET /api/v1/reports/scheduled
interface ScheduledReportList {
  reports: ScheduledReport[];
}

interface ScheduledReport {
  schedule_id: string;
  name: string;
  template_id: string;
  frequency: 'daily' | 'weekly' | 'monthly';
  recipients: string[];
  parameters: Record<string, any>;
  next_run: string;
  last_run: string;
  status: 'active' | 'paused';
}
```

### Generate Report
```typescript
// API: POST /api/v1/reports/generate
interface GenerateReportRequest {
  template_id?: string;
  report_type: string;
  date_range: { start: string; end: string };
  agencies?: string[];
  zones?: string[];
  format: 'pdf' | 'excel' | 'csv';
  parameters?: Record<string, any>;
}

interface GenerateReportResponse {
  report_id: string;
  status: 'generating' | 'completed' | 'failed';
  download_url?: string;
  error?: string;
}
```

### React Query
```typescript
const { data: templates } = useQuery({
  queryKey: ['reports', 'templates'],
  queryFn: () => api.get('/api/v1/reports/templates'),
});

const { data: scheduled } = useQuery({
  queryKey: ['reports', 'scheduled'],
  queryFn: () => api.get('/api/v1/reports/scheduled'),
});

const generateReport = useMutation({
  mutationFn: (request: GenerateReportRequest) =>
    api.post('/api/v1/reports/generate', request),
  onSuccess: (response) => {
    if (response.status === 'completed') {
      toast.success('Report generated');
      downloadFile(response.download_url);
    } else {
      toast.info('Report is being generated');
    }
  },
});
```

## Zustand Store
```typescript
// stores/reportsStore.ts
interface ReportsState {
  activeTab: string;
  generatingReport: boolean;
  setTab: (tab: string) => void;
  setGenerating: (generating: boolean) => void;
}
```

## Interactions

### Generate Report
1. Select report type
2. Configure parameters
3. Click Generate
4. Show progress
5. Download when complete

### Use Template
1. Click template card
2. Pre-fill parameters
3. Adjust if needed
4. Generate report

### Schedule Report
1. Click Schedule button
2. Set frequency
3. Add recipients
4. Save schedule

### Download Report
1. Click Download button
2. Choose format
3. Download file
4. Open in viewer

## Responsive Breakpoints

| Breakpoint | Layout |
|------------|--------|
| Desktop (>1024px) | Full tabs with form |
| Tablet (768-1024px) | Stacked tabs |
| Mobile (<768px) | Single tab view |

## Loading States
- Templates: Skeleton cards
- Scheduled: Skeleton table
- Generate: Progress indicator

## Error States
- Generation failure: Toast error
- Template error: Fallback to custom
- Network error: Retry button

## Accessibility
- Form fields are focusable
- Generation status announced via `aria-live`
- Screen reader: "Report generating..."
- Keyboard: Tab through form, Enter to submit

## Telemetry
- `reports.view` — Screen loaded
- `reports.generate` — Report generated
- `reports.template_use` — Template used
- `reports.schedule` — Report scheduled

## Implementation Notes
- ReportGenerator with form + preview
- TemplateLibrary for saved templates
- ScheduledReports for cron jobs
- AiDock provides report suggestions
- Export in multiple formats
