# ExecutiveHeader Component Contract

**Package**: `entities/executive`  
**Type**: Layout Component  
**Stability**: Stable  

---

## Purpose

Top-level header for executive workspace screens. Displays workspace title, key metrics summary, time period selector, and primary actions. Used in EXEC-001 Dashboard, EXEC-002 Pipeline, and EXEC-003 Reports screens.

---

## Props

```typescript
interface ExecutiveHeaderProps {
  /** Screen title */
  title: string;
  /** Subtitle/description */
  description?: string;
  /** Key metrics summary (shown as mini KPIs) */
  metrics?: ExecutiveMetric[];
  /** Time period selector */
  timePeriod?: {
    value: string;
    options: { label: string; value: string }[];
    onChange: (value: string) => void;
  };
  /** Primary actions */
  actions?: React.ReactNode;
  /** Breadcrumb items */
  breadcrumbs?: { label: string; href?: string }[];
  /** Loading state */
  loading?: boolean;
  /** Custom className */
  className?: string;
}

interface ExecutiveMetric {
  label: string;
  value: string | number;
  trend?: { value: number; isPositive: boolean };
  format?: 'number' | 'currency' | 'percentage' | 'compact';
}
```

---

## Slots

| Slot | Required | Description |
|------|----------|-------------|
| `title` | No | Custom title rendering |
| `metrics` | No | Custom metric cards |
| `actions` | No | Primary action buttons |
| `period` | No | Custom period selector |

---

## State

| State | Trigger | Visual |
|-------|---------|--------|
| `default` | Initial | Full header with all sections |
| `loading` | `loading=true` | Skeleton for metrics |
| `compact` | Mobile < 640px | Collapsed metrics, dropdown actions |
| `scrolled` | Page scroll > 100px | Sticky, shadow, reduced padding |

---

## Accessibility

- **Role**: `banner` (landmark)
- **Heading**: `h1` for title
- **Metrics**: `aria-label` per metric
- **Period Selector**: `aria-label="Time period"`
- **Sticky**: `position: sticky; top: 0; z-index: 40`

---

## Loading

- **Skeleton**: Title line + 3 metric skeletons
- **Delay**: 100ms

---

## Errors

Not applicable (display component)

---

## Keyboard

| Key | Action |
|-----|--------|
| `Tab` | Navigate period selector, actions |
| `Enter` | Activate period dropdown |

---

## Mobile

- **< 640px**: 
  - Title + description stacked
  - Metrics: horizontal scroll in KpiStrip
  - Actions: dropdown menu
  - Breadcrumbs: hidden (show in page title)

---

## Permissions

| Role | View |
|------|------|
| All authenticated | ✅ |

---

## Telemetry

| Event | Properties |
|-------|------------|
| `executive_header_view` | `screen`, `metric_count` |
| `executive_header_period_change` | `from`, `to` |
| `executive_header_action_click` | `action` |

---

## React Query

```typescript
// Metrics typically from executive/overview
const { data } = useQuery({
  queryKey: executiveKeys.overview(),
  select: (data) => ({
    totalPipeline: data.pipeline.estimated_total_pipeline_value_bdt,
    activeTenders: data.dashboard.total_tenders,
    winRate: data.win_probability,
    // ...
  })
});
```

---

## Dependencies

- `KpiStrip` (for metrics display)
- `PeriodSelector` (for time period)
- `Breadcrumb` (for navigation)
- `DropdownMenu` (for mobile actions)
- `lucide-react`: `TrendingUp`, `TrendingDown`, `Calendar`, `Filter`, `MoreHorizontal`

---

## Layout Structure

```
┌─────────────────────────────────────────────────────────────┐
│  Breadcrumb: Executive > Dashboard                          │
├─────────────────────────────────────────────────────────────┤
│  Title: "Executive Dashboard"                    [Period ▼] │
│  Description: "Real-time view of tender pipeline..."        │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ [Actions] │
│  │Pipeline │ │Win Rate │ │Avg NPP  │ │Active   │           │
│  │৳4.87B   │ │71%      │ │87.6%    │ │1,247    │           │
│  │↑ 12%    │ │↑ 3%     │ │↓ 0.4%   │ │↑ 8%     │           │
│  └─────────┘ └─────────┘ └─────────┘ └─────────┘           │
└─────────────────────────────────────────────────────────────┘
```

---

## Future Extensions

- [ ] Real-time metric updates via WebSocket
- [ ] Customizable metric selection
- [ ] Export header config
- [ ] Dark/light theme preview toggle