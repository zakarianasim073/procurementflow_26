# TRUST-011: System Logs Screen Specification

**Module:** `features/system-logs/SystemLogsPage`
**Layer:** features
**Version:** 1.0.0
**Status:** Draft
**Workspace:** Trust

## Purpose
System log viewing, filtering, and analysis for debugging and monitoring.

## Screen Layout

```
┌─────────────────────────────────────────────────────────────┐
│ ExecutiveHeader                                             │
├──────────┬──────────────────────────────────────────────────┤
│          │ Breadcrumb: Trust > System Logs                   │
│ Workspace├──────────────────────────────────────────────────┤
│   Nav    │ SystemLogsHeader (filters, search)               │
│          ├──────────────────────────────────────────────────┤
│          │ SystemLogs (main content)                        │
│          │ ┌────────────────────────────────────────────┐   │
│          │ │ FilterBar (level, source, date)             │   │
│          │ ├────────────────────────────────────────────┤   │
│          │ │ LogViewer (real-time log stream)            │   │
│          │ │ ┌──────────────────────────────────────────┐│   │
│          │ │ │ 10:00 [INFO] Server started              ││   │
│          │ │ │ 10:01 [DEBUG] Connection established     ││   │
│          │ │ │ 10:02 [WARN] Slow query detected         ││   │
│          │ │ │ ...                                      ││   │
│          │ │ └──────────────────────────────────────────┘│   │
│          │ ├────────────────────────────────────────────┤   │
│          │ │ LogAnalysis (error patterns, insights)     │   │
│          │ └────────────────────────────────────────────┘   │
├──────────┴──────────────────────────────────────────────────┤
│ AiDock (log insights, error analysis)                       │
└─────────────────────────────────────────────────────────────┘
```

## Component Tree

```
SystemLogsPage
├── ExecutiveHeader
├── Breadcrumb
├── SystemLogsHeader
│   ├── SearchBar (keyword search)
│   ├── ChipSelect (level: info/warn/error)
│   ├── ChipSelect (source)
│   ├── CalendarRange (date range)
│   └── Button (Export Logs)
├── SystemLogs
│   ├── FilterBar
│   │   ├── SearchBar (keyword)
│   │   ├── ChipSelect (level)
│   │   ├── ChipSelect (source)
│   │   └── CalendarRange (date)
│   ├── LogViewer
│   │   └── VirtualList<LogEntry>
│   │       └── LogLine × N
│   │           ├── timestamp
│   │           ├── level
│   │           ├── source
│   │           ├── message
│   │           └── details (expandable)
│   └── LogAnalysis
│       ├── Chart (error_frequency)
│       ├── Table<ErrorPattern>
│       │   ├── pattern
│       │   ├── count
│       │   └── last_occurrence
│       └── AiInsight × N
└── AiDock
    ├── AgentCard (Monitoring Agent)
    └── EvidencePanel (log insights)
```

## Data Sources

### System Logs
```typescript
// API: GET /api/v1/admin/logs
interface LogEntryList {
  entries: LogEntry[];
  total_count: number;
  has_more: boolean;
}

interface LogEntry {
  log_id: string;
  timestamp: string;
  level: 'debug' | 'info' | 'warn' | 'error';
  source: string;
  message: string;
  details?: Record<string, any>;
  stack_trace?: string;
}
```

### Log Analysis
```typescript
// API: GET /api/v1/admin/logs/analysis
interface LogAnalysis {
  error_frequency: { date: string; count: number }[];
  error_patterns: ErrorPattern[];
  insights: AiInsight[];
}

interface ErrorPattern {
  pattern: string;
  count: number;
  last_occurrence: string;
  sample: string;
}
```

### React Query
```typescript
const { data: logs } = useQuery({
  queryKey: ['admin', 'logs', filters],
  queryFn: () => api.get('/api/v1/admin/logs', { params: filters }),
  refetchInterval: 10_000, // 10 seconds
});

const { data: analysis } = useQuery({
  queryKey: ['admin', 'logs', 'analysis'],
  queryFn: () => api.get('/api/v1/admin/logs/analysis'),
});

const exportLogs = useMutation({
  mutationFn: (params: ExportParams) => api.post('/api/v1/admin/logs/export', params),
});
```

## Zustand Store
```typescript
// stores/systemLogsStore.ts
interface SystemLogsState {
  filters: {
    level: string[];
    source: string[];
    dateRange: { start: string; end: string } | null;
    keyword: string;
  };
  autoRefresh: boolean;
  setFilter: <K extends keyof SystemLogsState['filters']>(key: K, value: SystemLogsState['filters'][K]) => void;
  setAutoRefresh: (enabled: boolean) => void;
}
```

## Interactions

### Filter Logs
1. Apply filter
2. Reset pagination
3. Refetch logs
4. Update viewer

### View Details
1. Click log entry
2. Expand details
3. View stack trace
4. Analyze context

### Export Logs
1. Click Export button
2. Choose format
3. Include filters
4. Download file

### Analyze Patterns
1. View analysis section
2. Review error patterns
3. Read AI insights
4. Take action

## Responsive Breakpoints

| Breakpoint | Layout |
|------------|--------|
| Desktop (>1024px) | Full log viewer + analysis |
| Tablet (768-1024px) | Stacked view |
| Mobile (<768px) | Simplified log list |

## Loading States
- Logs: Skeleton rows
- Analysis: Skeleton charts
- Export: Progress indicator

## Error States
- Load failure: Retry button
- Export failure: Toast error
- Network error: Toast notification

## Accessibility
- Log entries are focusable
- Level changes announced via `aria-live`
- Screen reader: "Error: Connection failed"
- Keyboard: Arrow keys to navigate, Enter to expand

## Telemetry
- `system_logs.view` — Screen loaded
- `system_logs.filter` — Filter applied
- `system_logs.export` — Logs exported
- `system_logs.analysis_view` — Analysis viewed

## Implementation Notes
- Real-time log streaming
- VirtualList for performance
- Log analysis with patterns
- AiDock provides log insights
- Export for debugging
