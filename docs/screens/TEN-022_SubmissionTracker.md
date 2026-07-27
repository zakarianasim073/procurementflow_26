# TEN-022: Submission Tracker Screen Specification

**Module:** `features/submission-tracker/SubmissionTrackerPage`
**Layer:** features
**Version:** 1.0.0
**Status:** Draft
**Workspace:** Acquisition

## Purpose
Track tender submissions, deadlines, and status updates.

## Screen Layout

```
┌─────────────────────────────────────────────────────────────┐
│ ExecutiveHeader                                             │
├──────────┬──────────────────────────────────────────────────┤
│          │ Breadcrumb: Acquisition > Submission Tracker      │
│ Workspace├──────────────────────────────────────────────────┤
│   Nav    │ SubmissionTrackerHeader (count, upcoming)        │
│          ├──────────────────────────────────────────────────┤
│          │ SubmissionTracker (main content)                 │
│          │ ┌────────────────────────────────────────────┐   │
│          │ │ TimelineView (submissions timeline)         │   │
│          │ │ ┌──────────────────────────────────────────┐│   │
│          │ │ │ ●─── Tender A (Submitted)                ││   │
│          │ │ │ │                                        ││   │
│          │ │ │ ●─── Tender B (Pending)                  ││   │
│          │ │ │ │                                        ││   │
│          │ │ │ ●─── Tender C (Draft)                    ││   │
│          │ │ └──────────────────────────────────────────┘│   │
│          │ ├────────────────────────────────────────────┤   │
│          │ │ SubmissionList (detailed list)              │   │
│          │ └────────────────────────────────────────────┘   │
├──────────┴──────────────────────────────────────────────────┤
│ AiDock (submission insights)                                │
└─────────────────────────────────────────────────────────────┘
```

## Component Tree

```
SubmissionTrackerPage
├── ExecutiveHeader
├── Breadcrumb
├── SubmissionTrackerHeader
│   ├── KpiStrip (total_count, pending_count, upcoming_deadline)
│   └── Button (New Submission)
├── SubmissionTracker
│   ├── TimelineView
│   │   └── TimelineEntry × N
│   │       ├── status
│   │       ├── tender_name
│   │       ├── deadline
│   │       └── days_remaining
│   ├── SubmissionList
│   │   └── SubmissionCard × N
│   │       ├── tender_name
│   │       ├── agency
│   │       ├── status
│   │       ├── deadline
│   │       ├── documents
│   │       └── Button (View Details)
│   ├── SubmissionCalendar
│   │   └── CalendarView
│   │       └── DeadlineMarker × N
│   └── StatusBoard
│       ├── DraftColumn
│       ├── PendingColumn
│       ├── SubmittedColumn
│       └── AwardedColumn
└── AiDock
    ├── AgentCard (Submission Agent)
    └── EvidencePanel (submission insights)
```

## Data Sources

### Submissions
```typescript
// API: GET /api/v1/tenders/submissions
interface SubmissionList {
  submissions: Submission[];
  total_count: number;
  pending_count: number;
}

interface Submission {
  submission_id: string;
  tender_id: string;
  tender_name: string;
  agency: string;
  status: 'draft' | 'pending' | 'submitted' | 'awarded' | 'rejected';
  deadline: string;
  submitted_at?: string;
  documents: DocumentRef[];
  notes?: string;
}

interface DocumentRef {
  document_id: string;
  name: string;
  type: string;
  uploaded_at: string;
}
```

### React Query
```typescript
const { data: submissions } = useQuery({
  queryKey: ['tenders', 'submissions', filters],
  queryFn: () => api.get('/api/v1/tenders/submissions', { params: filters }),
});

const updateStatus = useMutation({
  mutationFn: ({ submissionId, status }: { submissionId: string; status: string }) =>
    api.patch(`/api/v1/tenders/submissions/${submissionId}`, { status }),
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ['tenders', 'submissions'] });
    toast.success('Status updated');
  },
});
```

## Zustand Store
```typescript
// stores/submissionTrackerStore.ts
interface SubmissionTrackerState {
  view: 'timeline' | 'list' | 'calendar' | 'board';
  filters: {
    status: string[];
    agency: string[];
    deadline: { start: string; end: string } | null;
  };
  setView: (view: string) => void;
  setFilter: <K extends keyof SubmissionTrackerState['filters']>(key: K, value: SubmissionTrackerState['filters'][K]) => void;
}
```

## Interactions

### View Submission
1. Click submission card
2. View details
3. Check documents
4. Review status

### Change Status
1. Click status dropdown
2. Select new status
3. Confirm change
4. Update view

### Filter Submissions
1. Apply filter
2. Update list
3. Preserve view
4. Refresh display

### Switch View
1. Click view toggle
2. Switch layout
3. Preserve filters
4. Update display

## Responsive Breakpoints

| Breakpoint | Layout |
|------------|--------|
| Desktop (>1024px) | Full timeline + list |
| Tablet (768-1024px) | List view |
| Mobile (<768px) | Simplified list |

## Loading States
- Timeline: Loading animation
- List: Skeleton cards
- Calendar: Loading view

## Error States
- Load failure: Retry button
- No submissions: EmptyState
- Network error: Toast notification

## Accessibility
- Submissions are focusable
- Status announced via `aria-live`
- Screen reader: "Tender A, status: submitted"
- Keyboard: Arrow keys to navigate

## Telemetry
- `submission_tracker.view` — Screen loaded
- `submission_tracker.view_change` — View changed
- `submission_tracker.status_update` — Status updated
- `submission_tracker.filter` — Filter applied

## Implementation Notes
- Multiple view modes
- Real-time status updates
- Deadline tracking
- AiDock provides submission insights
- Calendar integration
