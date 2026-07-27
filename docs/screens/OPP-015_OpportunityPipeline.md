# OPP-015: Opportunity Pipeline Screen Specification

**Module:** `features/opportunity-pipeline/OpportunityPipelinePage`
**Layer:** features
**Version:** 1.0.0
**Status:** Draft
**Workspace:** Opportunity

## Purpose
Visualize and manage opportunity pipeline stages and conversion.

## Screen Layout

```
┌─────────────────────────────────────────────────────────────┐
│ ExecutiveHeader                                             │
├──────────┬──────────────────────────────────────────────────┤
│          │ Breadcrumb: Opportunity > Opportunity Pipeline    │
│ Workspace├──────────────────────────────────────────────────┤
│   Nav    │ OpportunityPipelineHeader (count, conversion)    │
│          ├──────────────────────────────────────────────────┤
│          │ OpportunityPipeline (main content)               │
│          │ ┌────────────────────────────────────────────┐   │
│          │ │ PipelineBoard (Kanban view)                 │   │
│          │ │ ┌──────┬──────┬──────┬──────┬──────┐       │   │
│          │ │ │Lead  │Qualify│Proposal│Negotiate│Won │      │   │
│          │ │ │      │      │      │      │      │      │   │
│          │ │ │ 📋   │ 📋   │ 📋   │      │      │      │   │
│          │ │ │ 📋   │      │      │      │      │      │   │
│          │ │ └──────┴──────┴──────┴──────┴──────┘       │   │
│          │ ├────────────────────────────────────────────┤   │
│          │ │ PipelineMetrics (conversion rates)          │   │
│          │ └────────────────────────────────────────────┘   │
├──────────┴──────────────────────────────────────────────────┤
│ AiDock (pipeline insights)                                  │
└─────────────────────────────────────────────────────────────┘
```

## Component Tree

```
OpportunityPipelinePage
├── ExecutiveHeader
├── Breadcrumb
├── OpportunityPipelineHeader
│   ├── KpiStrip (opportunity_count, conversion_rate, avg_value)
│   └── Button (Add Opportunity)
├── OpportunityPipeline
│   ├── PipelineBoard
│   │   └── PipelineColumn × N
│   │       ├── stage_name
│   │       ├── count
│   │       └── OpportunityCard × N
│   │           ├── name
│   │           ├── value
│   │           ├── probability
│   │           ├── days_in_stage
│   │           └── Button (View Details)
│   ├── PipelineMetrics
│   │   ├── Chart (conversion_rates)
│   │   ├── Chart (stage_distribution)
│   │   └── Chart (value_by_stage)
│   ├── OpportunityDetails
│   │   ├── opportunity_info
│   │   ├── stage_history
│   │   └── next_actions
│   └── PipelineFilters
│       ├── ChipSelect (agency)
│       ├── ChipSelect (value_range)
│       └── ChipSelect (probability)
└── AiDock
    ├── AgentCard (Pipeline Agent)
    └── EvidencePanel (pipeline insights)
```

## Data Sources

### Opportunity Pipeline
```typescript
// API: GET /api/v1/opportunities/pipeline
interface OpportunityPipeline {
  opportunities: Opportunity[];
  stages: PipelineStage[];
  metrics: PipelineMetrics;
}

interface Opportunity {
  opportunity_id: string;
  name: string;
  agency: string;
  value: number;
  probability: number;
  stage: string;
  days_in_stage: number;
  created_at: string;
}

interface PipelineStage {
  stage_id: string;
  name: string;
  count: number;
  total_value: number;
}

interface PipelineMetrics {
  conversion_rates: { from: string; to: string; rate: number }[];
  avg_days_per_stage: { stage: string; days: number }[];
  total_value: number;
  weighted_value: number;
}
```

### React Query
```typescript
const { data: pipeline } = useQuery({
  queryKey: ['opportunities', 'pipeline'],
  queryFn: () => api.get('/api/v1/opportunities/pipeline'),
});

const moveOpportunity = useMutation({
  mutationFn: ({ opportunityId, stage }: { opportunityId: string; stage: string }) =>
    api.patch(`/api/v1/opportunities/${opportunityId}`, { stage }),
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ['opportunities', 'pipeline'] });
    toast.success('Opportunity moved');
  },
});
```

## Zustand Store
```typescript
// stores/opportunityPipelineStore.ts
interface OpportunityPipelineState {
  filters: {
    agency: string[];
    value_range: string[];
    probability: string[];
  };
  setFilter: <K extends keyof OpportunityPipelineState['filters']>(key: K, value: OpportunityPipelineState['filters'][K]) => void;
}
```

## Interactions

### View Opportunity
1. Click opportunity card
2. View details
3. Check stage history
4. Review next actions

### Move Opportunity
1. Drag opportunity
2. Drop in new stage
3. Update probability
4. Confirm move

### Filter Pipeline
1. Apply filters
2. Update board
3. Preserve view
4. Refresh metrics

### Analyze Metrics
1. View conversion rates
2. Check stage distribution
3. Review value analysis
4. Get recommendations

## Responsive Breakpoints

| Breakpoint | Layout |
|------------|--------|
| Desktop (>1024px) | Full Kanban board |
| Tablet (768-1024px) | Horizontal scroll |
| Mobile (<768px) | List view |

## Loading States
- Pipeline: Loading cards
- Metrics: Loading charts
- Details: Loading spinner

## Error States
- Move failure: Toast error
- Load failure: Retry button
- Network error: Toast notification

## Accessibility
- Cards are focusable
- Stage changes announced via `aria-live`
- Screen reader: "Opportunity: BWDB Project, stage: Proposal"
- Keyboard: Arrow keys to navigate

## Telemetry
- `opportunity_pipeline.view` — Screen loaded
- `opportunity_pipeline.move` — Opportunity moved
- `opportunity_pipeline.filter` — Filter applied

## Implementation Notes
- Kanban board
- Drag-and-drop
- Pipeline metrics
- AiDock provides pipeline insights
- Export for analysis
