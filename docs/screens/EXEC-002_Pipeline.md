# EXEC-002: Pipeline Overview Screen Specification

**Module:** `features/pipeline/PipelinePage`
**Layer:** features
**Version:** 1.0.0
**Status:** Draft
**Workspace:** Dashboard

## Purpose
Visual pipeline management for tender lifecycle stages with drag-and-drop progression and bulk operations.

## Screen Layout

```
┌─────────────────────────────────────────────────────────────┐
│ ExecutiveHeader                                             │
├──────────┬──────────────────────────────────────────────────┤
│          │ Breadcrumb: Dashboard > Pipeline                  │
│ Workspace├──────────────────────────────────────────────────┤
│   Nav    │ PipelineHeader (filters, view toggle)            │
│          ├──────────────────────────────────────────────────┤
│          │ PipelineView (main content)                      │
│          │ ┌────────────────────────────────────────────┐   │
│          │ │ Kanban Board (5 columns)                   │   │
│          │ │ ┌──────┬──────┬──────┬──────┬──────┐       │   │
│          │ │ │Discov│Qualif│Pricin│Compli│Submis│       │   │
│          │ │ │  y   │ catio│  ng  │ ance │ sion │       │   │
│          │ │ │      │  n   │      │      │      │       │   │
│          │ │ │ [T1] │ [T2] │ [T3] │ [T4] │ [T5] │       │   │
│          │ │ │ [T6] │ [T7] │      │ [T8] │      │       │   │
│          │ │ └──────┴──────┴──────┴──────┴──────┘       │   │
│          │ └────────────────────────────────────────────┘   │
├──────────┴──────────────────────────────────────────────────┤
│ AiDock (pipeline insights, stage recommendations)           │
└─────────────────────────────────────────────────────────────┘
```

## Component Tree

```
PipelinePage
├── ExecutiveHeader
├── Breadcrumb
├── PipelineHeader
│   ├── ChipSelect (agencies)
│   ├── ChipSelect (zones)
│   ├── RangeSlider (value range)
│   └── ViewToggle (kanban/list)
├── PipelineView
│   ├── KanbanBoard
│   │   └── KanbanColumn × 5
│   │       ├── Header (stage name, count)
│   │       └── TenderCard × N
│   │           ├── title
│   │           ├── agency
│   │           ├── value
│   │           ├── deadline
│   │           └── ConfidenceBadge (win_probability)
│   └── ListView
│       └── Table<Tender>
└── AiDock
    ├── AgentCard (Discovery Agent)
    └── EvidencePanel (pipeline insights)
```

## Data Sources

### Pipeline Data
```typescript
// API: GET /api/v1/dashboard/pipeline
interface PipelineData {
  stages: PipelineStage[];
  tenders: TenderSummary[];
}

interface PipelineStage {
  stage_id: string;
  name: string;
  count: number;
  total_value: number;
  avg_win_probability: number;
}

interface TenderSummary {
  tender_id: string;
  title: string;
  agency: string;
  zone: string;
  estimated_value: number;
  submission_deadline: string;
  current_stage: string;
  win_probability: number;
  stage_entered_at: string;
}
```

### Stage Transition
```typescript
// API: POST /api/v1/tenders/{tender_id}/stage
interface StageTransitionRequest {
  target_stage: string;
  notes?: string;
}

// API: POST /api/v1/tenders/bulk-stage
interface BulkStageTransitionRequest {
  tender_ids: string[];
  target_stage: string;
  notes?: string;
}
```

### React Query
```typescript
const { data: pipeline } = useQuery({
  queryKey: ['dashboard', 'pipeline', filters],
  queryFn: () => api.get('/api/v1/dashboard/pipeline', { params: filters }),
});

const transitionStage = useMutation({
  mutationFn: ({ tenderId, request }: { tenderId: string; request: StageTransitionRequest }) =>
    api.post(`/api/v1/tenders/${tenderId}/stage`, request),
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ['dashboard', 'pipeline'] });
    toast.success('Tender stage updated');
  },
});
```

## Zustand Store
```typescript
// stores/pipelineStore.ts
interface PipelineState {
  viewMode: 'kanban' | 'list';
  draggedTender: string | null;
  selectedTenders: Set<string>;
  setViewMode: (mode: string) => void;
  setDraggedTender: (id: string | null) => void;
  toggleSelect: (id: string) => void;
  clearSelection: () => void;
}
```

## Interactions

### Drag and Drop
1. Drag TenderCard
2. Drop on target column
3. Confirm transition
4. Update pipeline

### Bulk Move
1. Select multiple tenders
2. Click "Move to Stage"
3. Select target stage
4. Confirm bulk transition

### Tender Click
1. Click TenderCard
2. Open TenderDetail drawer
3. View details
4. Manual stage transition

### Filter Change
1. Update filters
2. Refetch pipeline
3. Preserve scroll position
4. Update column counts

## Responsive Breakpoints

| Breakpoint | Layout |
|------------|--------|
| Desktop (>1024px) | 5-column kanban |
| Tablet (768-1024px) | Horizontal scroll |
| Mobile (<768px) | List view, stage tabs |

## Loading States
- Columns: Skeleton cards
- Drag: Ghost card
- Transition: Spinner on card

## Error States
- Transition failure: Toast error
- Drag failure: Return to origin
- API error: Retry button

## Accessibility
- Cards are draggable
- Drop zones announced via `aria-live`
- Screen reader: "Move to Stage X"
- Keyboard: Space to pick up, Arrow to move, Enter to drop

## Telemetry
- `pipeline.view` — Screen loaded
- `pipeline.drag` — Tender dragged
- `pipeline.drop` — Tender dropped
- `pipeline.bulk_move` — Bulk transition

## Implementation Notes
- Kanban board with drag-and-drop
- Real-time updates via WebSocket
- AiDock provides pipeline insights
- Bulk operations for efficiency
- Responsive fallback to list view
