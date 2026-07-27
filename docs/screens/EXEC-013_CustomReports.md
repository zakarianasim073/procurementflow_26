# EXEC-013: Custom Reports Screen Specification

**Module:** `features/custom-reports/CustomReportsPage`
**Layer:** features
**Version:** 1.0.0
**Status:** Draft
**Workspace:** Dashboard

## Purpose
Build custom reports, dashboards, and data visualizations.

## Screen Layout

```
┌─────────────────────────────────────────────────────────────┐
│ ExecutiveHeader                                             │
├──────────┬──────────────────────────────────────────────────┤
│          │ Breadcrumb: Dashboard > Custom Reports            │
│ Workspace├──────────────────────────────────────────────────┤
│   Nav    │ CustomReportsHeader (report count, templates)    │
│          ├──────────────────────────────────────────────────┤
│          │ CustomReports (main content)                     │
│          │ ┌────────────────────────────────────────────┐   │
│          │ │ Tabs: [My Reports] [Templates] [Builder]   │   │
│          │ ├────────────────────────────────────────────┤   │
│          │ │ ReportList (saved reports)                  │   │
│          │ │ TemplateGallery (report templates)          │   │
│          │ │ ReportBuilder (drag & drop)                 │   │
│          │ └────────────────────────────────────────────┘   │
├──────────┴──────────────────────────────────────────────────┤
│ AiDock (report insights, suggestions)                       │
└─────────────────────────────────────────────────────────────┘
```

## Component Tree

```
CustomReportsPage
├── ExecutiveHeader
├── Breadcrumb
├── CustomReportsHeader
│   ├── KpiStrip (report_count, shared_count)
│   └── Button (Create Report)
├── CustomReports
│   ├── Tabs
│   │   ├── MyReportsTab
│   │   │   └── ReportList
│   │   │       └── ReportCard × N
│   │   │           ├── name
│   │   │           ├── description
│   │   │           ├── last_run
│   │   │           ├── share_count
│   │   │           └── actions (run, edit, share, delete)
│   │   ├── TemplatesTab
│   │   │   └── TemplateGallery
│   │   │       └── TemplateCard × N
│   │   │           ├── name
│   │   │           ├── description
│   │   │           ├── category
│   │   │           └── Button (Use Template)
│   │   └── BuilderTab
│   │       └── ReportBuilder
│   │           ├── DataSourcePanel
│   │           │   └── DataSource × N
│   │           │       ├── name
│   │           │       └── fields
│   │           ├── Canvas
│   │           │   └── Widget × N
│   │           │       ├── type (chart, table, kpi)
│   │           │       ├── config
│   │           │       └── data
│   │           └── PropertiesPanel
│   │               └── WidgetProperties
│   └── ReportPreview
│       ├── report_header
│       ├── widgets
│       └── export_options
└── AiDock
    ├── AgentCard (Analytics Agent)
    └── EvidencePanel (report insights)
```

## Data Sources

### Custom Reports
```typescript
// API: GET /api/v1/reports/custom
interface ReportList {
  reports: CustomReport[];
  total_count: number;
}

interface CustomReport {
  report_id: string;
  name: string;
  description: string;
  widgets: ReportWidget[];
  last_run: string;
  created_at: string;
  shared: boolean;
  share_count: number;
}

interface ReportWidget {
  widget_id: string;
  type: 'chart' | 'table' | 'kpi';
  title: string;
  config: Record<string, any>;
  data?: any;
  position: { x: number; y: number; w: number; h: number };
}
```

### Report Builder
```typescript
// API: POST /api/v1/reports/custom
interface CreateReportRequest {
  name: string;
  description: string;
  widgets: ReportWidget[];
}

// API: POST /api/v1/reports/custom/{report_id}/run
interface RunReportRequest {
  date_range?: { start: string; end: string };
  filters?: Record<string, any>;
}
```

### React Query
```typescript
const { data: reports } = useQuery({
  queryKey: ['reports', 'custom'],
  queryFn: () => api.get('/api/v1/reports/custom'),
});

const createReport = useMutation({
  mutationFn: (request: CreateReportRequest) => api.post('/api/v1/reports/custom', request),
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ['reports', 'custom'] });
    toast.success('Report created');
  },
});

const runReport = useMutation({
  mutationFn: ({ reportId, request }: { reportId: string; request: RunReportRequest }) =>
    api.post(`/api/v1/reports/custom/${reportId}/run`, request),
});
```

## Zustand Store
```typescript
// stores/customReportsStore.ts
interface CustomReportsState {
  activeTab: string;
  selectedReport: string | null;
  builderWidgets: ReportWidget[];
  setTab: (tab: string) => void;
  setReport: (id: string | null) => void;
  setWidgets: (widgets: ReportWidget[]) => void;
  addWidget: (widget: ReportWidget) => void;
  removeWidget: (widgetId: string) => void;
}
```

## Interactions

### View Reports
1. Click My Reports tab
2. View report list
3. Click report for details
4. Run report

### Use Template
1. Click Templates tab
2. Browse templates
3. Click Use Template
4. Customize in builder

### Build Report
1. Click Builder tab
2. Add widgets to canvas
3. Configure widgets
4. Save report

### Run Report
1. Click Run button
2. Set parameters
3. Execute query
4. View results

## Responsive Breakpoints

| Breakpoint | Layout |
|------------|--------|
| Desktop (>1024px) | Full builder with panels |
| Tablet (768-1024px) | Simplified builder |
| Mobile (<768px) | View-only mode |

## Loading States
- Reports: Skeleton cards
- Builder: Loading canvas
- Preview: Loading widgets

## Error States
- Create failure: Toast error
- Run failure: Error details
- Network error: Toast notification

## Accessibility
- Widgets are focusable
- Updates announced via `aria-live`
- Screen reader: "Chart: Sales by Region"
- Keyboard: Tab through widgets

## Telemetry
- `custom_reports.view` — Screen loaded
- `custom_reports.create` — Report created
- `custom_reports.run` — Report run
- `custom_reports.share` — Report shared

## Implementation Notes
- Drag-and-drop report builder
- Widget library (charts, tables, KPIs)
- Template gallery
- AiDock provides report insights
- Export to PDF/Excel
