# ENT-019: System Maintenance Screen Specification

**Module:** `features/system-maintenance/SystemMaintenancePage`
**Layer:** features
**Version:** 1.0.0
**Status:** Draft
**Workspace:** Settings

## Purpose
System health monitoring, maintenance tasks, and diagnostics.

## Screen Layout

```
┌─────────────────────────────────────────────────────────────┐
│ ExecutiveHeader                                             │
├──────────┬──────────────────────────────────────────────────┤
│          │ Breadcrumb: Settings > System Maintenance         │
│ Workspace├──────────────────────────────────────────────────┤
│   Nav    │ SystemMaintenanceHeader (health, tasks)          │
│          ├──────────────────────────────────────────────────┤
│          │ SystemMaintenance (main content)                 │
│          │ ┌────────────────────────────────────────────┐   │
│          │ │ Tabs: [Health] [Tasks] [Diagnostics]        │   │
│          │ ├────────────────────────────────────────────┤   │
│          │ │ HealthPanel (system health)                 │   │
│          │ │ TasksPanel (maintenance tasks)              │   │
│          │ │ DiagnosticsPanel (system diagnostics)       │   │
│          │ └────────────────────────────────────────────┘   │
├──────────┴──────────────────────────────────────────────────┤
│ AiDock (maintenance insights)                               │
└─────────────────────────────────────────────────────────────┘
```

## Component Tree

```
SystemMaintenancePage
├── ExecutiveHeader
├── Breadcrumb
├── SystemMaintenanceHeader
│   ├── KpiStrip (health_score, uptime, tasks_running)
│   └── Button (Run Diagnostics)
├── SystemMaintenance
│   ├── Tabs
│   │   ├── HealthTab
│   │   │   └── HealthPanel
│   │   │       ├── HealthIndicator × N
│   │   │       │   ├── component
│   │   │       │   ├── status
│   │   │       │   └── details
│   │   │       └── HealthChart (history)
│   │   ├── TasksTab
│   │   │   └── TasksPanel
│   │   │       ├── TaskList
│   │   │       │   └── TaskCard × N
│   │   │       │       ├── name
│   │   │       │       ├── status
│   │   │       │       ├── last_run
│   │   │       │       └── Button (Run Now)
│   │   │       └── TaskHistory
│   │   │           └── HistoryEntry × N
│   │   └── DiagnosticsTab
│   │       └── DiagnosticsPanel
│   │           ├── SystemInfo
│   │           │   ├── version
│   │           │   ├── uptime
│   │           │   └── resources
│   │           ├── LogViewer
│   │           │   └── LogEntry × N
│   │           └── BenchmarkResults
│   │               └── Benchmark × N
│   └── MaintenanceLog
│       └── LogEntry × N
│           ├── date
│           ├── action
│           └── result
└── AiDock
    ├── AgentCard (System Agent)
    └── EvidencePanel (maintenance insights)
```

## Data Sources

### System Health
```typescript
// API: GET /api/v1/admin/maintenance/health
interface SystemHealth {
  health_score: number;
  uptime: number;
  components: ComponentHealth[];
  history: { timestamp: string; score: number }[];
}

interface ComponentHealth {
  name: string;
  status: 'healthy' | 'degraded' | 'down';
  details: string;
  last_check: string;
}
```

### Maintenance Tasks
```typescript
// API: GET /api/v1/admin/maintenance/tasks
interface MaintenanceTask {
  task_id: string;
  name: string;
  description: string;
  status: 'idle' | 'running' | 'completed' | 'failed';
  last_run: string;
  next_run: string;
  history: TaskRun[];
}

interface TaskRun {
  run_id: string;
  started_at: string;
  completed_at: string;
  status: string;
  details: string;
}
```

### React Query
```typescript
const { data: health } = useQuery({
  queryKey: ['admin', 'maintenance', 'health'],
  queryFn: () => api.get('/api/v1/admin/maintenance/health'),
  refetchInterval: 30_000,
});

const { data: tasks } = useQuery({
  queryKey: ['admin', 'maintenance', 'tasks'],
  queryFn: () => api.get('/api/v1/admin/maintenance/tasks'),
});

const runTask = useMutation({
  mutationFn: (taskId: string) => api.post(`/api/v1/admin/maintenance/tasks/${taskId}/run`),
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ['admin', 'maintenance', 'tasks'] });
    toast.success('Task started');
  },
});
```

## Zustand Store
```typescript
// stores/systemMaintenanceStore.ts
interface SystemMaintenanceState {
  activeTab: string;
  setTab: (tab: string) => void;
}
```

## Interactions

### View Health
1. Click Health tab
2. View components
3. Check status
4. Review history

### Run Task
1. Click Run Now button
2. Start task
3. Show progress
4. Display result

### Run Diagnostics
1. Click Run Diagnostics
2. Execute system check
3. Display results
4. Show recommendations

### View Logs
1. Click LogViewer
2. Filter logs
3. Search entries
4. View details

## Responsive Breakpoints

| Breakpoint | Layout |
|------------|--------|
| Desktop (>1024px) | Full tabs with panels |
| Tablet (768-1024px) | Stacked tabs |
| Mobile (<768px) | Simplified view |

## Loading States
- Health: Loading indicators
- Tasks: Skeleton cards
- Diagnostics: Loading spinner

## Error States
- Health check failure: Retry button
- Task failure: Error details
- Network error: Toast notification

## Accessibility
- Components are focusable
- Status announced via `aria-live`
- Screen reader: "Database: healthy"
- Keyboard: Tab through components

## Telemetry
- `system_maintenance.view` — Screen loaded
- `system_maintenance.task_run` — Task run
- `system_maintenance.diagnostics` — Diagnostics run
- `system_maintenance.health_check` — Health check

## Implementation Notes
- Real-time health monitoring
- Task scheduling and execution
- System diagnostics
- AiDock provides maintenance insights
- Log viewer for debugging
