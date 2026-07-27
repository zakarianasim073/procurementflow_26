# AgentCard Component Contract

**Package**: `widgets/ai`  
**Type**: AI Agent Display Component  
**Stability**: Stable  

---

## Purpose

Displays an AI agent's status, capabilities, and execution controls. Used in agent management dashboard, pipeline visualization, and agent marketplace.

---

## Props

```typescript
interface AgentCardProps {
  /** Agent metadata */
  agent: {
    id: string;
    name: string;
    description: string;
    category: 'discovery' | 'acquisition' | 'evaluation' | 'intelligence' | 'competitor' | 'pricing' | 'decision' | 'knowledge' | 'learning';
    version: string;
    status: 'idle' | 'ready' | 'running' | 'success' | 'error' | 'maintenance';
    capabilities: string[];
    dependencies: string[];
    timeoutSeconds: number;
    retryPolicy: { maxAttempts: number; delayMs: number };
    metrics: {
      executionsToday: number;
      successRate: number;
      avgExecutionTimeMs: number;
      lastExecutedAt?: string;
    };
  };
  /** Display variant */
  variant?: 'default' | 'compact' | 'detailed' | 'marketplace';
  /** Show execution controls */
  showControls?: boolean;
  /** Execution handler */
  onExecute?: (agentId: string, context: Record<string, any>) => void;
  /** View details handler */
  onViewDetails?: (agentId: string) => void;
  /** Custom className */
  className?: string;
}
```

---

## Slots

| Slot | Required | Description |
|------|----------|-------------|
| `header` | No | Custom status badge, version |
| `metrics` | No | Custom metric display |
| `actions` | No | Custom action buttons |

---

## State

| State | Trigger | Visual |
|-------|---------|--------|
| `idle` | `status='idle'` | Gray badge, "Ready to run" |
| `ready` | `status='ready'` | Green badge, "Ready" |
| `running` | `status='running'` | Blue pulsing badge, spinner, progress bar |
| `success` | `status='success'` | Green badge, checkmark, "Completed" |
| `error` | `status='error'` | Red badge, error icon, "Failed" |
| `maintenance` | `status='maintenance'` | Orange badge, tool icon, "Maintenance" |
| `hover` | Mouse enter | Subtle elevation, border highlight |

---

## Accessibility

- **Role**: `article` with `aria-label="Agent: [name], status [status]"`
- **Status**: `aria-live="polite"` for status changes
- **Controls**: Buttons with `aria-label="Run [agent name]"`
- **Keyboard**: Tab through controls, Enter activates
- **Screen Reader**: Announces status changes

---

## Loading

- **Skeleton**: Card outline + metric skeletons
- **Execution**: Progress bar replaces status badge

---

## Errors

- **Execution Failed**: Inline error with retry button
- **Agent Unavailable**: Disabled card with maintenance notice

---

## Keyboard

| Key | Action |
|-----|--------|
| `Tab` | Navigate controls |
| `Enter` / `Space` | Execute agent / View details |
| `Escape` | Cancel execution (if running) |

---

## Mobile

- **< 640px**: Stacked layout, full-width buttons
- **Controls**: Bottom action bar
- **Metrics**: Collapsible

---

## Permissions

| Role | View | Execute | Configure |
|------|------|---------|-----------|
| `viewer` | ✅ | ❌ | ❌ |
| `estimator` | ✅ | ✅ (assigned) | ❌ |
| `admin` | ✅ | ✅ | ✅ |

---

## Telemetry

| Event | Properties |
|-------|------------|
| `agent_card_view` | `agent_id`, `variant` |
| `agent_execute` | `agent_id`, `context_keys` |
| `agent_details_view` | `agent_id` |

---

## React Query

```typescript
const { data } = useQuery({
  queryKey: agentKeys.detail(agentId),
  select: (data) => ({
    ...data,
    status: data.status || 'idle',
    metrics: data.metrics || {}
  })
});
```

---

## Dependencies

- `StatusBadge` (for status display)
- `ProgressRing` (for execution progress)
- `CapabilityTags` (for capabilities)
- `Button` (for controls)
- `Tooltip` (for capability descriptions)
- `lucide-react`: `Bot`, `Play`, `Pause`, `CheckCircle`, `AlertCircle`, `Settings`, `ExternalLink`

---

## Category Color Coding

| Category | Color | Icon |
|----------|-------|------|
| discovery | Blue | `Search` |
| acquisition | Green | `Download` |
| evaluation | Orange | `CheckSquare` |
| intelligence | Purple | `Brain` |
| competitor | Red | `Users` |
| pricing | Green | `DollarSign` |
| decision | Indigo | `Gavel` |
| knowledge | Teal | `Database` |
| learning | Pink | `GraduationCap` |

---

## Future Extensions

- [ ] Real-time status via WebSocket
- [ ] Execution history popover
- [ ] Parameter schema viewer
- [ ] Agent comparison mode
- [ ] Marketplace install/uninstall