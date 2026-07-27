# EXEC-001: Executive Dashboard Screen Specification

**Module:** `features/dashboard/DashboardPage`
**Layer:** features
**Version:** 1.0.0
**Status:** Draft
**Workspace:** Dashboard

## Purpose
Central command center providing real-time KPIs, pipeline overview, agency analytics, and AI-powered recommendations across all active tenders and opportunities.

## Screen Layout

```
┌─────────────────────────────────────────────────────────────┐
│ ExecutiveHeader (workspace switcher, search, notifications) │
├──────────┬──────────────────────────────────────────────────┤
│          │ KpiStrip (8 KPI cards in scrollable row)         │
│ Workspace├──────────────────────────────────────────────────┤
│   Nav    │ AiDock (AI assistant, contextual actions)        │
│          ├──────────────────────────────────────────────────┤
│ 6 work-  │ Main Content Area                                │
│ spaces   │ ┌─────────────────────┬─────────────────────┐    │
│          │ │ TenderPipeline      │ AgencySpendChart     │    │
│          │ │ (Kanban 5 stages)   │ (Bar chart by zone)  │    │
│          │ ├─────────────────────┼─────────────────────┤    │
│          │ │ WinProbability      │ CompetitorHeatmap    │    │
│          │ │ (Gauge + Sparkline) │ (Grid visualization) │    │
│          │ ├─────────────────────┴─────────────────────┤    │
│          │ │ ActivityTimeline (recent actions + AI)     │    │
│          │ └───────────────────────────────────────────┘    │
├──────────┴──────────────────────────────────────────────────┤
│ TrustPanel (AI confidence, data freshness, model status)    │
└─────────────────────────────────────────────────────────────┘
```

## Component Tree

```
DashboardPage
├── ExecutiveHeader
│   ├── WorkspaceSwitcher
│   ├── SearchBar (global search)
│   └── NotificationBell
├── KpiStrip
│   ├── KpiCard (totalTenders)
│   ├── KpiCard (activePipeline)
│   ├── KpiCard (winRate)
│   ├── KpiCard (avgBidValue)
│   ├── KpiCard (pendingApprovals)
│   ├── KpiCard (agentActivity)
│   ├── KpiCard (dataFreshness)
│   └── KpiCard (complianceScore)
├── AiDock
│   ├── AgentCard (quick actions)
│   └── EvidencePanel (AI suggestions)
├── TenderPipeline (widgets)
├── AgencySpendChart (widgets)
├── WinProbability (widgets)
├── CompetitorHeatmap (widgets)
├── ActivityTimeline (widgets)
└── TrustPanel
```

## Data Sources

### KPI Strip
```typescript
// API: GET /api/v1/dashboard/stats
interface DashboardStats {
  total_tenders: number;
  active_pipeline: number;
  win_rate: number;
  avg_bid_value: number;
  pending_approvals: number;
  agent_runs_today: number;
  data_freshness_hours: number;
  compliance_score: number;
}

// React Query
const { data: stats } = useQuery({
  queryKey: ['dashboard', 'stats'],
  queryFn: () => api.get('/api/v1/dashboard/stats'),
  refetchInterval: 300_000, // 5 minutes
});
```

### Tender Pipeline
```typescript
// API: GET /api/v1/dashboard/pipeline
interface PipelineStage {
  stage: 'discovery' | 'qualification' | 'pricing' | 'compliance' | 'submission';
  count: number;
  total_value: number;
  avg_win_probability: number;
}
```

### Agency Spend
```typescript
// API: GET /api/v1/dashboard/agency-spend
interface AgencySpend {
  agency: string;
  month: string;
  awarded_count: number;
  total_value: number;
  zone_breakdown: Record<string, number>;
}
```

### Competitor Heatmap
```typescript
// API: GET /api/v1/dashboard/competitor-heatmap
interface CompetitorHeatmapEntry {
  division: string;
  district: string;
  competitor_count: number;
  avg_bid_ratio: number;
  activity_level: 'low' | 'medium' | 'high';
}
```

## Zustand Store
```typescript
// stores/dashboardStore.ts
interface DashboardState {
  selectedTimeRange: '7d' | '30d' | '90d' | '1y';
  selectedAgencies: string[];
  selectedZones: string[];
  setTimeRange: (range: string) => void;
  setAgencies: (agencies: string[]) => void;
  setZones: (zones: string[]) => void;
}
```

## Interactions

### KPI Card Click
1. Navigate to filtered view (e.g., tender list filtered by stage)
2. Update URL params: `/dashboard?stage=discovery`
3. Highlight corresponding pipeline stage

### Pipeline Stage Click
1. Navigate to `/discovery?stage={stage}`
2. Pass filter context via URL params

### AI Dock Action
1. User selects quick action from AiDock
2. Agent runs in background
3. ActivityTimeline updates with new entry
4. Toast notification on completion

### Competitor Heatmap Hover
1. Show tooltip with detailed metrics
2. Click to open Competitor Detail drawer

## Responsive Breakpoints

| Breakpoint | Layout |
|------------|--------|
| Desktop (>1024px) | Full 2-column grid |
| Tablet (768-1024px) | Single column, collapsed nav |
| Mobile (<768px) | Stacked cards, bottom nav |

## Loading States
- KpiStrip: 8 skeleton cards
- Pipeline: 5 skeleton columns
- Charts: Skeleton with shimmer
- Timeline: 5 skeleton rows

## Error States
- Network error: Full-screen error with retry
- Partial data: Show available KPIs, gray out missing
- Agent failure: TrustPanel shows warning

## Accessibility
- Skip to main content link
- KPI values announced via `aria-live="polite"`
- Chart data available as table fallback
- Keyboard navigation through all sections

## Telemetry
- `dashboard.view` — Screen loaded (load time)
- `dashboard.kpi_click` — KPI card clicked
- `dashboard.pipeline_click` — Stage clicked
- `dashboard.ai_action` — AI dock action triggered
- `dashboard.time_range` — Time range changed

## Implementation Notes
- Real page with actual API integration (reference implementation)
- Uses `useQuery` for all data fetching
- Responsive with Tailwind breakpoints
- AiDock provides contextual AI assistance
- TrustPanel shows system health and AI confidence
