# OPP-003: Bulk Operations Screen Specification

**Module:** `features/bulk/BulkOperationsPage`
**Layer:** features
**Version:** 1.0.0
**Status:** Draft
**Workspace:** Discovery

## Purpose
Batch processing of tenders, bulk AI analysis, mass updates, and bulk export operations.

## Screen Layout

```
┌─────────────────────────────────────────────────────────────┐
│ ExecutiveHeader                                             │
├──────────┬──────────────────────────────────────────────────┤
│          │ Breadcrumb: Discovery > Bulk Operations           │
│ Workspace├──────────────────────────────────────────────────┤
│   Nav    │ BulkOperationsHeader (queue, progress)           │
│          ├──────────────────────────────────────────────────┤
│          │ BulkOperations (main content)                    │
│          │ ┌────────────────────────────────────────────┐   │
│          │ │ Tabs: [Select] [Process] [History]         │   │
│          │ ├────────────────────────────────────────────┤   │
│          │ │ TenderSelector (filter + select)            │   │
│          │ │ ProcessOptions (batch actions)              │   │
│          │ │ ProcessingHistory (past batches)            │   │
│          │ └────────────────────────────────────────────┘   │
├──────────┴──────────────────────────────────────────────────┤
│ AiDock (batch recommendations, optimization)                │
└─────────────────────────────────────────────────────────────┘
```

## Component Tree

```
BulkOperationsPage
├── ExecutiveHeader
├── Breadcrumb
├── BulkOperationsHeader
│   ├── KpiStrip (queue_size, processing, completed)
│   └── Badge (active_batches)
├── BulkOperations
│   ├── Tabs
│   │   ├── SelectTab
│   │   │   └── TenderSelector
│   │   │       ├── FilterPanel
│   │   │       ├── TenderList (selectable)
│   │   │       │   └── TenderCard × N
│   │   │       │       ├── checkbox
│   │   │       │       ├── title
│   │   │       │       └── agency
│   │   │       └── Button (Select All Matching)
│   │   ├── ProcessTab
│   │   │   └── ProcessOptions
│   │   │       ├── Select (action: analyze/qualify/export)
│   │   │       ├── ChipSelect (options)
│   │   │       ├── Progress (batch progress)
│   │   │       └── Button (Start Batch)
│   │   └── HistoryTab
│   │       └── ProcessingHistory
│   │           └── Table<BatchJob>
│   │               ├── name
│   │               ├── action
│   │               ├── status
│   │               ├── progress
│   │               └── completed_at
│   └── BatchProgress
│       ├── Progress (overall)
│       ├── Table<ProcessedItem>
│       │   ├── tender_id
│       │   ├── status
│       │   └── result
│       └── Button (Cancel All)
└── AiDock
    ├── AgentCard (Pipeline Agent)
    └── EvidencePanel (batch insights)
```

## Data Sources

### Batch Jobs
```typescript
// API: GET /api/v1/tenders/bulk/jobs
interface BatchJobList {
  jobs: BatchJob[];
  active_count: number;
}

interface BatchJob {
  job_id: string;
  name: string;
  action: string;
  status: 'queued' | 'processing' | 'completed' | 'failed' | 'cancelled';
  total_items: number;
  processed_items: number;
  failed_items: number;
  created_at: string;
  completed_at?: string;
  error?: string;
}

interface ProcessedItem {
  tender_id: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  result?: any;
  error?: string;
}
```

### Start Batch
```typescript
// API: POST /api/v1/tenders/bulk/start
interface StartBatchRequest {
  name: string;
  action: string;
  tender_ids: string[];
  options?: Record<string, any>;
}

interface StartBatchResponse {
  job_id: string;
  status: 'queued' | 'processing';
  estimated_duration: number;
}
```

### React Query
```typescript
const { data: jobs } = useQuery({
  queryKey: ['tenders', 'bulk', 'jobs'],
  queryFn: () => api.get('/api/v1/tenders/bulk/jobs'),
  refetchInterval: 10_000, // 10 seconds
});

const startBatch = useMutation({
  mutationFn: (request: StartBatchRequest) =>
    api.post('/api/v1/tenders/bulk/start', request),
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ['tenders', 'bulk'] });
    toast.success('Batch job started');
  },
});

const cancelBatch = useMutation({
  mutationFn: (jobId: string) => api.post(`/api/v1/tenders/bulk/${jobId}/cancel`),
});
```

## Zustand Store
```typescript
// stores/bulkOperationsStore.ts
interface BulkOperationsState {
  activeTab: string;
  selectedTenders: Set<string>;
  currentJob: string | null;
  setTab: (tab: string) => void;
  toggleSelect: (id: string) => void;
  selectAll: (ids: string[]) => void;
  clearSelection: () => void;
  setCurrentJob: (id: string | null) => void;
}
```

## Interactions

### Tender Selection
1. Use filters to narrow list
2. Click checkboxes to select
3. Or click "Select All Matching"
4. View selection count

### Start Batch
1. Select action type
2. Configure options
3. Click Start Batch
4. Show confirmation
5. Start processing

### Monitor Progress
1. View progress bar
2. See processed/failed counts
3. Cancel if needed
4. View results when complete

### View History
1. Click History tab
2. View past batches
3. Click job for details
4. Download results

## Responsive Breakpoints

| Breakpoint | Layout |
|------------|--------|
| Desktop (>1024px) | Full tabs with lists |
| Tablet (768-1024px) | Stacked tabs |
| Mobile (<768px) | Single tab view |

## Loading States
- Tender list: Skeleton rows
- Batch progress: Progress bar
- History: Skeleton table

## Error States
- Batch failure: Error details
- Item failure: Retry individual
- Network error: Toast notification

## Accessibility
- Checkboxes are focusable
- Progress announced via `aria-live`
- Screen reader: "Processing X of Y"
- Keyboard: Space to select, Enter to start

## Telemetry
- `bulk_operations.view` — Screen loaded
- `bulk_operations.select` — Tenders selected
- `bulk_operations.start` — Batch started
- `bulk_operations.cancel` — Batch cancelled

## Implementation Notes
- TenderSelector with filter + select
- ProcessOptions for batch actions
- Real-time progress monitoring
- AiDock provides batch insights
- History for audit trail
