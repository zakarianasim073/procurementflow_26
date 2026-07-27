# ENT-018: Error Logs Screen Specification

**Module:** `features/error-logs/ErrorLogsPage`
**Layer:** features
**Version:** 1.0.0
**Status:** Draft
**Workspace:** Settings

## Purpose
Error tracking, log analysis, and debugging tools.

## Screen Layout

```
┌─────────────────────────────────────────────────────────────┐
│ ExecutiveHeader                                             │
├──────────┬──────────────────────────────────────────────────┤
│          │ Breadcrumb: Settings > Error Logs                 │
│ Workspace├──────────────────────────────────────────────────┤
│   Nav    │ ErrorLogsHeader (error count, severity)          │
│          ├──────────────────────────────────────────────────┤
│          │ ErrorLogs (main content)                         │
│          │ ┌────────────────────────────────────────────┐   │
│          │ │ FilterBar (severity, source, date)          │   │
│          │ ├────────────────────────────────────────────┤   │
│          │ │ ErrorList (error entries)                   │   │
│          │ │ ┌──────────────────────────────────────────┐│   │
│          │ │ │ Error: Connection timeout at 10:00       ││   │
│          │ │ │ Error: Invalid input at 10:05            ││   │
│          │ │ │ ...                                      ││   │
│          │ │ └──────────────────────────────────────────┘│   │
│          │ ├────────────────────────────────────────────┤   │
│          │ │ ErrorAnalysis (patterns, insights)         │   │
│          │ └────────────────────────────────────────────┘   │
├──────────┴──────────────────────────────────────────────────┤
│ AiDock (error insights, fix suggestions)                    │
└─────────────────────────────────────────────────────────────┘
```

## Component Tree

```
ErrorLogsPage
├── ExecutiveHeader
├── Breadcrumb
├── ErrorLogsHeader
│   ├── KpiStrip (error_count, critical_count, warning_count)
│   └── Button (Clear Old Logs)
├── ErrorLogs
│   ├── FilterBar
│   │   ├── ChipSelect (severity)
│   │   ├── ChipSelect (source)
│   │   ├── CalendarRange (date range)
│   │   └── SearchBar (keyword)
│   ├── ErrorList
│   │   └── VirtualList<ErrorEntry>
│   │       └── ErrorCard × N
│   │           ├── severity
│   │           ├── message
│   │           ├── source
│   │           ├── timestamp
│   │           ├── count
│   │           └── Button (View Details)
│   └── ErrorAnalysis
│       ├── Chart (error_frequency)
│       ├── Table<ErrorPattern>
│       │   ├── pattern
│       │   ├── count
│       │   └── last_occurrence
│       └── AiInsight × N
└── AiDock
    ├── AgentCard (Debug Agent)
    └── EvidencePanel (error insights)
```

## Data Sources

### Error Logs
```typescript
// API: GET /api/v1/admin/errors
interface ErrorLogList {
  errors: ErrorEntry[];
  total_count: number;
}

interface ErrorEntry {
  error_id: string;
  severity: 'info' | 'warning' | 'error' | 'critical';
  message: string;
  source: string;
  stack_trace?: string;
  count: number;
  first_occurrence: string;
  last_occurrence: string;
  metadata?: Record<string, any>;
}
```

### Error Analysis
```typescript
// API: GET /api/v1/admin/errors/analysis
interface ErrorAnalysis {
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
const { data: errors } = useQuery({
  queryKey: ['admin', 'errors', filters],
  queryFn: () => api.get('/api/v1/admin/errors', { params: filters }),
  refetchInterval: 30_000, // 30 seconds
});

const { data: analysis } = useQuery({
  queryKey: ['admin', 'errors', 'analysis'],
  queryFn: () => api.get('/api/v1/admin/errors/analysis'),
});

const clearLogs = useMutation({
  mutationFn: (olderThan: string) => api.delete('/api/v1/admin/errors', { params: { older_than: olderThan } }),
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ['admin', 'errors'] });
    toast.success('Old logs cleared');
  },
});
```

## Zustand Store
```typescript
// stores/errorLogsStore.ts
interface ErrorLogsState {
  filters: {
    severity: string[];
    source: string[];
    dateRange: { start: string; end: string } | null;
    keyword: string;
  };
  setFilter: <K extends keyof ErrorLogsState['filters']>(key: K, value: ErrorLogsState['filters'][K]) => void;
}
```

## Interactions

### Filter Errors
1. Apply filter
2. Refetch errors
3. Update list
4. Preserve selection

### View Details
1. Click error card
2. Expand details
3. View stack trace
4. Analyze context

### Clear Logs
1. Click Clear button
2. Select age
3. Confirm clear
4. Update list

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
| Mobile (<768px) | Simplified error list |

## Loading States
- Errors: Skeleton cards
- Analysis: Skeleton charts
- Export: Progress indicator

## Error States
- Load failure: Retry button
- Clear failure: Toast error
- Network error: Toast notification

## Accessibility
- Error cards are focusable
- Severity announced via `aria-live`
- Screen reader: "Error: Connection timeout"
- Keyboard: Arrow keys to navigate, Enter to expand

## Telemetry
- `error_logs.view` — Screen loaded
- `error_logs.filter` — Filter applied
- `error_logs.clear` — Logs cleared
- `error_logs.view_details` — Details viewed

## Implementation Notes
- Real-time error monitoring
- VirtualList for performance
- Error analysis with patterns
- AiDock provides error insights
- Export for debugging
