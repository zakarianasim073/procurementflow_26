# ENT-029: System Logs Viewer Screen Specification

**Module:** `features/system-logs-viewer/SystemLogsViewerPage`
**Layer:** features
**Version:** 1.0.0
**Status:** Draft
**Workspace:** Settings

## Purpose
Advanced system log viewing, searching, and analysis.

## Screen Layout

```
┌─────────────────────────────────────────────────────────────┐
│ ExecutiveHeader                                             │
├──────────┬──────────────────────────────────────────────────┤
│          │ Breadcrumb: Settings > System Logs Viewer         │
│ Workspace├──────────────────────────────────────────────────┤
│   Nav    │ SystemLogsViewerHeader (count, level)            │
│          ├──────────────────────────────────────────────────┤
│          │ SystemLogsViewer (main content)                  │
│          │ ┌────────────────────────────────────────────┐   │
│          │ │ FilterBar (level, source, date)             │   │
│          │ ├────────────────────────────────────────────┤   │
│          │ │ LogTable (log entries)                      │   │
│          │ │ ┌──────────────────────────────────────────┐│   │
│          │ │ │ [INFO] 10:00:00 Server started           ││   │
│          │ │ │ [WARN] 10:05:00 High memory usage        ││   │
│          │ │ │ [ERROR] 10:10:00 Connection failed        ││   │
│          │ │ └──────────────────────────────────────────┘│   │
│          │ ├────────────────────────────────────────────┤   │
│          │ │ LogDetails (selected log)                   │   │
│          │ └────────────────────────────────────────────┘   │
├──────────┴──────────────────────────────────────────────────┤
│ AiDock (log insights)                                       │
└─────────────────────────────────────────────────────────────┘
```

## Component Tree

```
SystemLogsViewerPage
├── ExecutiveHeader
├── Breadcrumb
├── SystemLogsViewerHeader
│   ├── KpiStrip (log_count, error_count, warning_count)
│   └── Button (Export Logs)
├── SystemLogsViewer
│   ├── FilterBar
│   │   ├── ChipSelect (level)
│   │   ├── ChipSelect (source)
│   │   ├── CalendarRange (date_range)
│   │   └── SearchBar (keyword)
│   ├── LogTable
│   │   └── Table<LogEntry>
│   │       ├── timestamp
│   │       ├── level
│   │       ├── source
│   │       ├── message
│   │       └── actions (view, copy)
│   ├── LogDetails
│   │   ├── log_info
│   │   ├── stack_trace
│   │   ├── context
│   │   └── related_logs
│   └── LogStats
│       ├── chart (level_distribution)
│       ├── chart (source_distribution)
│       └── chart (timeline)
└── AiDock
    ├── AgentCard (Debug Agent)
    └── EvidencePanel (log insights)
```

## Data Sources

### System Logs
```typescript
// API: GET /api/v1/admin/logs
interface SystemLogs {
  logs: LogEntry[];
  total_count: number;
  error_count: number;
  warning_count: number;
}

interface LogEntry {
  log_id: string;
  level: 'debug' | 'info' | 'warn' | 'error' | 'critical';
  timestamp: string;
  source: string;
  message: string;
  stack_trace?: string;
  context?: Record<string, any>;
}
```

### React Query
```typescript
const { data: logs } = useQuery({
  queryKey: ['admin', 'logs', filters],
  queryFn: () => api.get('/api/v1/admin/logs', { params: filters }),
  refetchInterval: 10_000,
});
```

## Zustand Store
```typescript
// stores/systemLogsViewerStore.ts
interface SystemLogsViewerState {
  selectedLog: string | null;
  filters: {
    level: string[];
    source: string[];
    date_range: { start: string; end: string } | null;
    keyword: string;
  };
  setLog: (id: string | null) => void;
  setFilter: <K extends keyof SystemLogsViewerState['filters']>(key: K, value: SystemLogsViewerState['filters'][K]) => void;
}
```

## Interactions

### Filter Logs
1. Apply filter
2. Update table
3. Preserve selection
4. Refresh display

### View Details
1. Click log entry
2. View details
3. Check stack trace
4. See context

### Export Logs
1. Click Export
2. Choose format
3. Apply filters
4. Download file

### Copy Log
1. Click Copy button
2. Copy to clipboard
3. Paste elsewhere
4. Share with team

## Responsive Breakpoints

| Breakpoint | Layout |
|------------|--------|
| Desktop (>1024px) | Full table + details |
| Tablet (768-1024px) | Table with modal details |
| Mobile (<768px) | Simplified list |

## Loading States
- Logs: Skeleton rows
- Details: Loading spinner
- Stats: Loading charts

## Error States
- Load failure: Retry button
- Export failure: Toast error
- Network error: Toast notification

## Accessibility
- Logs are focusable
- Level announced via `aria-live`
- Screen reader: "ERROR at 10:10: Connection failed"
- Keyboard: Arrow keys to navigate

## Telemetry
- `system_logs_viewer.view` — Screen loaded
- `system_logs_viewer.filter` — Filter applied
- `system_logs_viewer.view_details` — Details viewed
- `system_logs_viewer.export` — Logs exported

## Implementation Notes
- Advanced log filtering
- Real-time updates
- Log analysis
- AiDock provides log insights
- Export for debugging
