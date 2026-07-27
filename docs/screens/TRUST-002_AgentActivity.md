# TRUST-002: Agent Activity Monitor Screen Specification

**Module:** `features/agent-activity/AgentActivityPage`
**Layer:** features
**Version:** 1.0.0
**Status:** Draft
**Workspace:** Trust

## Purpose
Monitor AI agent execution, view run history, manage agent configurations, and track system health.

## Screen Layout

```
┌─────────────────────────────────────────────────────────────┐
│ ExecutiveHeader                                             │
├──────────┬──────────────────────────────────────────────────┤
│          │ Breadcrumb: Trust > Agent Activity               │
│ Workspace├──────────────────────────────────────────────────┤
│   Nav    │ AgentActivityHeader (stats, filters)             │
│          ├──────────────────────────────────────────────────┤
│          │ AgentActivityMonitor (main content)              │
│          │ ┌────────────────────────────────────────────┐   │
│          │ │ AgentList (cards grid)                      │   │
│          │ │ ┌──────────┐ ┌──────────┐ ┌──────────┐     │   │
│          │ │ │ Agent 1  │ │ Agent 2  │ │ Agent 3  │     │   │
│          │ │ │ Status:  │ │ Status:  │ │ Status:  │     │   │
│          │ │ │ Running  │ │ Idle     │ │ Error    │     │   │
│          │ │ └──────────┘ └──────────┘ └──────────┘     │   │
│          │ ├────────────────────────────────────────────┤   │
│          │ │ RunHistory (table)                          │   │
│          │ │ Agent | Status | Duration | Result          │   │
│          │ │ ───────────────────────────────────────────│   │
│          │ │ Disc  | Run    | 2m 30s   | Success        │   │
│          │ │ Acq   | Run    | 5m 15s   | Partial        │   │
│          │ ├────────────────────────────────────────────┤   │
│          │ │ SystemHealth (metrics)                      │   │
│          │ │ CPU: 45% | Memory: 62% | Queue: 3          │   │
│          │ └────────────────────────────────────────────┘   │
├──────────┴──────────────────────────────────────────────────┤
│ TrustPanel (agent confidence, system status)                │
└─────────────────────────────────────────────────────────────┘
```

## Component Tree

```
AgentActivityPage
├── ExecutiveHeader
├── Breadcrumb
├── AgentActivityHeader
│   ├── KpiStrip (active_agents, total_runs, success_rate, avg_duration)
│   └── FilterPanel (status, agent_type, date_range)
├── AgentActivityMonitor
│   ├── AgentList
│   │   └── AgentCard × N
│   │       ├── Avatar (agent icon)
│   │       ├── Badge (status)
│   │       ├── KpiCard (last_run)
│   │       └── Button (View Runs)
│   ├── RunHistory
│   │   └── Table<AgentRun>
│   └── SystemHealth
│       ├── Gauge (cpu_usage)
│       ├── Gauge (memory_usage)
│       └── Badge (queue_size)
└── TrustPanel
```

## Data Sources

### Agent Status
```typescript
// API: GET /api/v1/ai/agents
interface AgentStatus {
  agent_id: string;
  name: string;
  category: string;
  status: 'idle' | 'running' | 'error' | 'disabled';
  last_run?: string;
  last_result?: string;
  total_runs: number;
  success_rate: number;
  avg_duration: number;
}
```

### Run History
```typescript
// API: GET /api/v1/ai/runs
interface AgentRun {
  run_id: string;
  agent_id: string;
  agent_name: string;
  status: 'running' | 'completed' | 'failed' | 'cancelled';
  started_at: string;
  completed_at?: string;
  duration?: number;
  input?: any;
  output?: any;
  error?: string;
  confidence?: number;
}
```

### System Health
```typescript
// API: GET /api/v1/ai/health
interface SystemHealth {
  cpu_usage: number;
  memory_usage: number;
  queue_size: number;
  active_connections: number;
  model_status: Record<string, 'online' | 'offline' | 'degraded'>;
}
```

### React Query
```typescript
const { data: agents } = useQuery({
  queryKey: ['ai', 'agents'],
  queryFn: () => api.get('/api/v1/ai/agents'),
  refetchInterval: 10_000, // 10 seconds
});

const { data: runs } = useQuery({
  queryKey: ['ai', 'runs', filters],
  queryFn: () => api.get('/api/v1/ai/runs', { params: filters }),
});

const { data: health } = useQuery({
  queryKey: ['ai', 'health'],
  queryFn: () => api.get('/api/v1/ai/health'),
  refetchInterval: 30_000, // 30 seconds
});

const cancelRun = useMutation({
  mutationFn: (runId: string) => api.post(`/api/v1/ai/runs/${runId}/cancel`),
});
```

## Zustand Store
```typescript
// stores/agentActivityStore.ts
interface AgentActivityState {
  selectedAgent: string | null;
  filterStatus: string[];
  filterAgentType: string[];
  dateRange: { start: string; end: string } | null;
  setSelectedAgent: (id: string | null) => void;
  setFilter: (key: string, value: any) => void;
}
```

## Interactions

### Agent Card Click
1. Click AgentCard
2. Highlight in list
3. Show run history for that agent
4. Display configuration details

### Run History View
1. Click run row
2. Open RunDetails drawer
3. Show input/output/error
4. View execution logs

### Cancel Run
1. Click Cancel button on running agent
2. Confirm cancellation
3. POST cancel API
4. Update status in real-time

### System Health
1. View CPU/Memory gauges
2. Click gauge for detailed metrics
3. Monitor queue size
4. View model status

## Responsive Breakpoints

| Breakpoint | Layout |
|------------|--------|
| Desktop (>1024px) | Grid cards + table |
| Tablet (768-1024px) | Stacked cards |
| Mobile (<768px) | List view, bottom details |

## Loading States
- Agent cards: Skeleton cards
- Run history: Skeleton table
- Health metrics: Skeleton gauges

## Error States
- Agent offline: Warning badge
- Run failed: Error details in drawer
- System overload: Warning toast

## Accessibility
- Agent cards are focusable
- Status changes announced via `aria-live`
- Screen reader: "Agent X, status: running"
- Keyboard: Enter to select, Escape to deselect

## Telemetry
- `agent_activity.view` — Screen loaded
- `agent_activity.select` — Agent selected
- `agent_activity.cancel` — Run cancelled
- `agent_activity.filter` — Filter applied

## Implementation Notes
- Real-time updates via WebSocket
- Agent cards show live status
- Run history sortable and filterable
- System health monitored continuously
- AiDock provides agent management
