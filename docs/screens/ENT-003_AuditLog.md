# ENT-003: Audit Log Screen Specification

**Module:** `features/audit/AuditLogPage`
**Layer:** features
**Version:** 1.0.0
**Status:** Draft
**Workspace:** Settings

## Purpose
Audit trail viewing, compliance reporting, and activity monitoring for regulatory compliance.

## Screen Layout

```
┌─────────────────────────────────────────────────────────────┐
│ ExecutiveHeader                                             │
├──────────┬──────────────────────────────────────────────────┤
│          │ Breadcrumb: Settings > Audit Log                  │
│ Workspace├──────────────────────────────────────────────────┤
│   Nav    │ AuditLogHeader (date range, filters)             │
│          ├──────────────────────────────────────────────────┤
│          │ AuditLog (main content)                          │
│          │ ┌────────────────────────────────────────────┐   │
│          │ │ FilterBar (user, action, resource, date)   │   │
│          │ ├────────────────────────────────────────────┤   │
│          │ │ AuditTable (sortable, filterable)          │   │
│          │ │ Time | User | Action | Resource | Details  │   │
│          │ │ ───────────────────────────────────────────│   │
│          │ │ 10:00 | John | Create | Tender #123 | ...  │   │
│          │ │ 09:50 | Jane | Update | BOQ #456 | ...     │   │
│          │ ├────────────────────────────────────────────┤   │
│          │ │ Pagination                                 │   │
│          │ └────────────────────────────────────────────┘   │
├──────────┴──────────────────────────────────────────────────┤
│ AiDock (audit insights, anomaly detection)                  │
└─────────────────────────────────────────────────────────────┘
```

## Component Tree

```
AuditLogPage
├── ExecutiveHeader
├── Breadcrumb
├── AuditLogHeader
│   ├── CalendarRange (date range)
│   ├── ChipSelect (users)
│   ├── ChipSelect (actions)
│   ├── ChipSelect (resources)
│   └── Button (Export Report)
├── AuditLog
│   ├── FilterBar
│   │   ├── SearchBar (keyword)
│   │   ├── ChipSelect (user)
│   │   ├── ChipSelect (action)
│   │   └── ChipSelect (resource)
│   ├── AuditTable
│   │   └── Table<AuditEntry>
│   │       ├── timestamp
│   │       ├── user
│   │       ├── action
│   │       ├── resource
│   │       ├── details
│   │       └── ip_address
│   └── Pagination
└── AiDock
    ├── AgentCard (Admin Agent)
    └── EvidencePanel (audit insights)
```

## Data Sources

### Audit Entries
```typescript
// API: GET /api/v1/audit
interface AuditLog {
  entries: AuditEntry[];
  total_count: number;
  page: number;
  size: number;
}

interface AuditEntry {
  entry_id: string;
  timestamp: string;
  user_id: string;
  user_name: string;
  action: string;
  resource_type: string;
  resource_id: string;
  details?: Record<string, any>;
  ip_address: string;
  user_agent: string;
}
```

### Audit Summary
```typescript
// API: GET /api/v1/audit/summary
interface AuditSummary {
  total_entries: number;
  actions_breakdown: Record<string, number>;
  users_breakdown: Record<string, number>;
  resources_breakdown: Record<string, number>;
  date_range: { start: string; end: string };
}
```

### React Query
```typescript
const { data: auditLog } = useQuery({
  queryKey: ['audit', filters],
  queryFn: () => api.get('/api/v1/audit', { params: filters }),
});

const { data: summary } = useQuery({
  queryKey: ['audit', 'summary', dateRange],
  queryFn: () => api.get('/api/v1/audit/summary', { params: dateRange }),
});

const exportAudit = useMutation({
  mutationFn: (params: ExportParams) => api.post('/api/v1/audit/export', params),
});
```

## Zustand Store
```typescript
// stores/auditLogStore.ts
interface AuditLogState {
  filters: {
    dateRange: { start: string; end: string } | null;
    users: string[];
    actions: string[];
    resources: string[];
    keyword: string;
  };
  page: number;
  size: number;
  setFilter: (key: string, value: any) => void;
  setPage: (page: number) => void;
  setSize: (size: number) => void;
}
```

## Interactions

### Filter Change
1. Update filter
2. Reset page to 1
3. Refetch audit log
4. Update summary

### Entry Details
1. Click entry row
2. Open AuditDrawer
3. View full details
4. View related entries

### Export Report
1. Click Export button
2. Choose date range
3. Select format (CSV/PDF)
4. Download report

### Pagination
1. Click page number
2. Refetch with new page
3. Preserve filters
4. Scroll to top

## Responsive Breakpoints

| Breakpoint | Layout |
|------------|--------|
| Desktop (>1024px) | Full table with filters |
| Tablet (768-1024px) | Collapsible filters |
| Mobile (<768px) | Card view, bottom pagination |

## Loading States
- Table: Skeleton rows
- Summary: Skeleton cards
- Export: Progress indicator

## Error States
- Load failure: Retry button
- Export failure: Toast error
- Network error: Retry button

## Accessibility
- Table rows are focusable
- Filter changes announced via `aria-live`
- Screen reader: "Entry X of Y"
- Keyboard: Arrow keys to navigate, Enter to expand

## Telemetry
- `audit_log.view` — Screen loaded
- `audit_log.filter` — Filter applied
- `audit_log.export` — Report exported
- `audit_log.entry_view` — Entry viewed

## Implementation Notes
- Filterable audit table
- Pagination for large datasets
- Export for compliance reporting
- AiDock provides audit insights
- Real-time updates via WebSocket
