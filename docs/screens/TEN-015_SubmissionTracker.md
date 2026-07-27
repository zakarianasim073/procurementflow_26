# TEN-015: Submission Tracker Screen Specification

**Module:** `features/submission-tracker/SubmissionTrackerPage`
**Layer:** features
**Version:** 1.0.0
**Status:** Draft
**Workspace:** Acquisition

## Purpose
Track tender submissions, monitor status, and manage post-submission activities.

## Screen Layout

```
┌─────────────────────────────────────────────────────────────┐
│ ExecutiveHeader                                             │
├──────────┬──────────────────────────────────────────────────┤
│          │ Breadcrumb: Acquisition > Submission Tracker      │
│ Workspace├──────────────────────────────────────────────────┤
│   Nav    │ SubmissionTrackerHeader (stats, filters)         │
│          ├──────────────────────────────────────────────────┤
│          │ SubmissionTracker (main content)                 │
│          │ ┌────────────────────────────────────────────┐   │
│          │ │ KpiStrip (submission metrics)               │   │
│          │ ├────────────────────────────────────────────┤   │
│          │ │ Tabs: [Active] [Submitted] [Awarded]       │   │
│          │ │ [Rejected]                                  │   │
│          │ ├────────────────────────────────────────────┤   │
│          │ │ ActiveList (pending submissions)            │   │
│          │ │ SubmittedList (submitted tenders)           │   │
│          │ │ AwardedList (awarded tenders)               │   │
│          │ │ RejectedList (rejected tenders)             │   │
│          │ └────────────────────────────────────────────┘   │
├──────────┴──────────────────────────────────────────────────┤
│ AiDock (submission insights, recommendations)               │
└─────────────────────────────────────────────────────────────┘
```

## Component Tree

```
SubmissionTrackerPage
├── ExecutiveHeader
├── Breadcrumb
├── SubmissionTrackerHeader
│   ├── KpiStrip (total_submitted, pending, awarded, rejected)
│   └── Button (Export Report)
├── SubmissionTracker
│   ├── Tabs
│   │   ├── ActiveTab
│   │   │   └── ActiveList
│   │   │       └── TenderCard × N
│   │   │           ├── title
│   │   │           ├── agency
│   │   │           ├── deadline
│   │   │           ├── status
│   │   │           └── Button (Submit)
│   │   ├── SubmittedTab
│   │   │   └── SubmittedList
│   │   │       └── TenderCard × N
│   │   │           ├── title
│   │   │           ├── agency
│   │   │           ├── submitted_at
│   │   │           ├── status
│   │   │           └── Button (View)
│   │   ├── AwardedTab
│   │   │   └── AwardedList
│   │   │       └── TenderCard × N
│   │   │           ├── title
│   │   │           ├── agency
│   │   │           ├── award_value
│   │   │           └── Button (View)
│   │   └── RejectedTab
│   │       └── RejectedList
│   │           └── TenderCard × N
│   │               ├── title
│   │               ├── agency
│   │               ├── rejection_reason
│   │               └── Button (View)
│   └── SubmissionDetail
│       ├── tender_info
│       ├── submission_status
│       └── next_steps
└── AiDock
    ├── AgentCard (Decision Agent)
    └── EvidencePanel (submission insights)
```

## Data Sources

### Submissions
```typescript
// API: GET /api/v1/tenders/submissions
interface SubmissionList {
  submissions: Submission[];
  total_count: number;
}

interface Submission {
  submission_id: string;
  tender_id: string;
  title: string;
  agency: string;
  status: 'active' | 'submitted' | 'awarded' | 'rejected';
  submitted_at?: string;
  awarded_at?: string;
  award_value?: number;
  rejection_reason?: string;
  win_probability?: number;
}
```

### React Query
```typescript
const { data: submissions } = useQuery({
  queryKey: ['tenders', 'submissions', status],
  queryFn: () => api.get('/api/v1/tenders/submissions', { params: { status } }),
  refetchInterval: 60_000, // 1 minute
});

const submitTender = useMutation({
  mutationFn: (tenderId: string) => api.post(`/api/v1/tenders/${tenderId}/submit`),
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ['tenders', 'submissions'] });
    toast.success('Tender submitted');
  },
});
```

## Zustand Store
```typescript
// stores/submissionTrackerStore.ts
interface SubmissionTrackerState {
  activeTab: string;
  setTab: (tab: string) => void;
}
```

## Interactions

### View Active
1. Click Active tab
2. View pending submissions
3. Click tender for details
4. Submit when ready

### View Submitted
1. Click Submitted tab
2. View submitted tenders
3. Monitor status
4. Track progress

### View Awarded
1. Click Awarded tab
2. View awarded tenders
3. Review award details
4. Proceed to contract

### View Rejected
1. Click Rejected tab
2. View rejected tenders
3. Review rejection reason
4. Learn from feedback

## Responsive Breakpoints

| Breakpoint | Layout |
|------------|--------|
| Desktop (>1024px) | Full tabs with cards |
| Tablet (768-1024px) | Stacked tabs |
| Mobile (<768px) | Single tab view |

## Loading States
- Submissions: Skeleton cards
- Detail: Skeleton content
- Stats: Skeleton cards

## Error States
- Load failure: Retry button
- Submit failure: Toast error
- Network error: Toast notification

## Accessibility
- Cards are focusable
- Stats announced via `aria-live`
- Screen reader: "X submissions, Y awarded"
- Keyboard: Enter to view, Tab to navigate

## Telemetry
- `submission_tracker.view` — Screen loaded
- `submission_tracker.submit` — Tender submitted
- `submission_tracker.tab_switch` — Tab changed
- `submission_tracker.export` — Report exported

## Implementation Notes
- Tab-based submission tracking
- Status-based filtering
- Award/rejection tracking
- AiDock provides submission insights
- Export for reporting
