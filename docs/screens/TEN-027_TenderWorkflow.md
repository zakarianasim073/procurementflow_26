# TEN-027: Tender Workflow Screen Specification

**Module:** `features/tender-workflow/TenderWorkflowPage`
**Layer:** features
**Version:** 1.0.0
**Status:** Draft
**Workspace:** Acquisition

## Purpose
Visualize and manage tender lifecycle workflows and stages.

## Screen Layout

```
┌─────────────────────────────────────────────────────────────┐
│ ExecutiveHeader                                             │
├──────────┬──────────────────────────────────────────────────┤
│          │ Breadcrumb: Acquisition > Tender Workflow         │
│ Workspace├──────────────────────────────────────────────────┤
│   Nav    │ TenderWorkflowHeader (tender, stage)             │
│          ├──────────────────────────────────────────────────┤
│          │ TenderWorkflow (main content)                    │
│          │ ┌────────────────────────────────────────────┐   │
│          │ │ WorkflowVisual (stage pipeline)             │   │
│          │ │ ┌──────┬──────┬──────┬──────┬──────┐       │   │
│          │ │ │Draft │Review│Submit│Award │Complete│      │   │
│          │ │ │  ✓   │  ✓   │  ●   │  ○   │  ○    │      │   │
│          │ │ └──────┴──────┴──────┴──────┴──────┘       │   │
│          │ ├────────────────────────────────────────────┤   │
│          │ │ StageDetails (current stage)                │   │
│          │ └────────────────────────────────────────────┘   │
├──────────┴──────────────────────────────────────────────────┤
│ AiDock (workflow insights)                                  │
└─────────────────────────────────────────────────────────────┘
```

## Component Tree

```
TenderWorkflowPage
├── ExecutiveHeader
├── Breadcrumb
├── TenderWorkflowHeader
│   ├── tender_info
│   ├── current_stage
│   └── Button (Update Stage)
├── TenderWorkflow
│   ├── WorkflowVisual
│   │   ├── Stage × N
│   │   │   ├── name
│   │   │   ├── status (completed, current, pending)
│   │   │   ├── due_date
│   │   │   └── Button (View Details)
│   │   └── ProgressBar
│   ├── StageDetails
│   │   ├── stage_info
│   │   ├── requirements
│   │   ├── checklist
│   │   └── Button (Complete Stage)
│   ├── WorkflowHistory
│   │   └── HistoryEntry × N
│   │       ├── stage
│   │       ├── action
│   │       ├── user
│   │       └── timestamp
│   └── WorkflowMetrics
│       ├── avg_stage_duration
│       ├── bottleneck_analysis
│       └── completion_rate
└── AiDock
    ├── AgentCard (Workflow Agent)
    └── EvidencePanel (workflow insights)
```

## Data Sources

### Tender Workflow
```typescript
// API: GET /api/v1/tenders/{tender_id}/workflow
interface TenderWorkflow {
  tender_id: string;
  tender_name: string;
  current_stage: string;
  stages: WorkflowStage[];
  history: WorkflowHistory[];
  metrics: WorkflowMetrics;
}

interface WorkflowStage {
  stage_id: string;
  name: string;
  status: 'completed' | 'current' | 'pending';
  due_date?: string;
  completed_at?: string;
  requirements: string[];
  checklist: ChecklistItem[];
}

interface ChecklistItem {
  item_id: string;
  description: string;
  completed: boolean;
}

interface WorkflowHistory {
  entry_id: string;
  stage: string;
  action: string;
  user_id: string;
  user_name: string;
  timestamp: string;
  details?: Record<string, any>;
}

interface WorkflowMetrics {
  avg_stage_duration: number;
  total_duration: number;
  completion_rate: number;
  bottleneck_stage?: string;
}
```

### React Query
```typescript
const { data: workflow } = useQuery({
  queryKey: ['tenders', tenderId, 'workflow'],
  queryFn: () => api.get(`/api/v1/tenders/${tenderId}/workflow`),
  enabled: !!tenderId,
});

const updateStage = useMutation({
  mutationFn: ({ tenderId, stageId, action }: { tenderId: string; stageId: string; action: string }) =>
    api.post(`/api/v1/tenders/${tenderId}/workflow/stages/${stageId}`, { action }),
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ['tenders', tenderId, 'workflow'] });
    toast.success('Stage updated');
  },
});
```

## Zustand Store
```typescript
// stores/tenderWorkflowStore.ts
interface TenderWorkflowState {
  selectedStage: string | null;
  setStage: (id: string | null) => void;
}
```

## Interactions

### View Stage
1. Click stage
2. View details
3. Check requirements
4. Review checklist

### Complete Stage
1. Click Complete Stage
2. Check all items
3. Confirm completion
4. Update workflow

### View History
1. View history list
2. Check actions
3. Review users
4. See timestamps

### Analyze Metrics
1. View metrics
2. Check duration
3. Identify bottlenecks
4. Get recommendations

## Responsive Breakpoints

| Breakpoint | Layout |
|------------|--------|
| Desktop (>1024px) | Full workflow + details |
| Tablet (768-1024px) | Stacked layout |
| Mobile (<768px) | Simplified pipeline |

## Loading States
- Workflow: Loading stages
- Details: Loading spinner
- Metrics: Loading charts

## Error States
- Update failure: Toast error
- Load failure: Retry button
- Network error: Toast notification

## Accessibility
- Stages are focusable
- Status announced via `aria-live`
- Screen reader: "Stage: Submit, status: current"
- Keyboard: Arrow keys to navigate

## Telemetry
- `tender_workflow.view` — Screen loaded
- `tender_workflow.stage_update` — Stage updated
- `tender_workflow.stage_complete` — Stage completed

## Implementation Notes
- Visual workflow pipeline
- Stage management
- Checklist system
- AiDock provides workflow insights
- Metrics and analytics
