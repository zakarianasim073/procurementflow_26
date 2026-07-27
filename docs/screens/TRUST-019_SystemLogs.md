# TRUST-019: System Logs Screen Specification

**Module:** `features/system-logs/SystemLogsPage`
**Layer:** features
**Version:** 1.0.0
**Status:** Draft
**Workspace:** Trust

## Purpose
View, search, and analyze system logs and audit trails.

## Screen Layout

```
┌─────────────────────────────────────────────────────────────┐
│ ExecutiveHeader                                             │
├──────────┬──────────────────────────────────────────────────┤
│          │ Breadcrumb: Trust > System Logs                   │
│ Workspace├──────────────────────────────────────────────────┤
│   Nav    │ SystemLogsHeader (count, level)                  │
│          ├──────────────────────────────────────────────────┤
│          │ SystemLogs (main content)                        │
│          │ ┌────────────────────────────────────────────┐   │
│          │ │ FilterBar (level, source, date)             │   │
│          │ ├────────────────────────────────────────────┤   │
│          │ │ LogList (log entries)                       │   │
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
SystemLogsPage
├── ExecutiveHeader
├── Breadcrumb
├── SystemLogsHeader
│   ├── KpiStrip (log_count, error_count, warning_count)
│   └── Button (Export Logs)
├── SystemLogs
│   ├── FilterBar
│   │   ├── ChipSelect (level: INFO, WARN, ERROR)
│   │   ├── ChipSelect (source)
│   │   ├── CalendarRange (date_range)
│   │   └── SearchBar (keyword)
│   ├── LogList
│   │   └── VirtualList<LogEntry>
│   │       └── LogCard × N
│   │           ├── level
│   │           ├── timestamp
│   │           ├── source
│   │           ├── message
│   │           └── Button (View Details)
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
// API: GET /api/v1/trust/logs
interface SystemLogs {
  logs: LogEntry[];
  total_count: number;
  error_count: number;
  warning_count: number;
}

interface LogEntry {
  log_id: string;
  level: 'info' | 'warn' | 'error' | 'debug';
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
  queryKey: ['trust', 'logs', filters],
  queryFn: () => api.get('/api/v1/trust/logs', { params: filters }),
  refetchInterval: 10_000, // 10 seconds
});

const { data: logDetails } = useQuery({
  queryKey: ['trust', 'logs', logId],
  queryFn: () => api.get(`/api/v1/trust/logs/${logId}`),
  enabled: !!logId,
});
```

## Zustand Store
```typescript
// stores/systemLogsStore.ts
interface SystemLogsState {
  selectedLog: string | null;
  filters: {
    level: string[];
    source: string[];
    dateRange: { start: string; end: string } | null;
    keyword: string;
  };
  setLog: (id: string | null) => void;
  setFilter: <K extends keyof SystemLogsState['filters']>(key: K, value: SystemLogsState['filters'][K]) => void;
}
```

## Interactions

### Filter Logs
1. Apply filter
2. Update list
3. Preserve selection
4. Refresh display

### View Details
1. Click log card
2. View details
3. Check stack trace
4. See context

### Export Logs
1. Click Export
2. Choose format
3. Apply filters
4. Download file

### Search Logs
1. Type keyword
2. Search logs
3. Highlight matches
4. Navigate results

## Responsive Breakpoints

| Breakpoint | Layout |
|------------|--------|
| Desktop (>1024px) | Full list + details |
| Tablet (768-1024px) | List with modal details |
| Mobile (<768px) | Simplified list |

## Loading States
- Logs: Skeleton cards
- Details: Loading spinner
- Search: Loading indicator

## Error States
- Load failure: Retry button
- No logs: EmptyState
- Network error: Toast notification

## Accessibility
- Logs are focusable
- Level announced via `aria-live`
- Screen reader: "ERROR at 10:10: Connection failed"
- Keyboard: Arrow keys to navigate

## Telemetry
- `system_logs.view` — Screen loaded
- `system_logs.filter` — Filter applied
- `system_logs.view_details` — Details viewed
- `system_logs.export` — Logs exported

## Implementation Notes
- Real-time log streaming
- Advanced filtering
- Log analysis
- AiDock provides log insights
- Export for debugging
