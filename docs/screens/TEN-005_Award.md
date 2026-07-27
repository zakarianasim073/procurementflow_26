# TEN-005: Award Tracking Screen Specification

**Module:** `features/awards/AwardPage`
**Layer:** features
**Version:** 1.0.0
**Status:** Draft
**Workspace:** Acquisition

## Purpose
Track tender awards, contract management, performance monitoring, and post-award analytics.

## Screen Layout

```
┌─────────────────────────────────────────────────────────────┐
│ ExecutiveHeader                                             │
├──────────┬──────────────────────────────────────────────────┤
│          │ Breadcrumb: Acquisition > Awards > {Award}       │
│ Workspace├──────────────────────────────────────────────────┤
│   Nav    │ AwardHeader (award summary, status badge)        │
│          ├──────────────────────────────────────────────────┤
│          │ AwardTracker (main content)                      │
│          │ ┌────────────────────────────────────────────┐   │
│          │ │ Status: Awarded                            │   │
│          │ ├────────────────────────────────────────────┤   │
│          │ │ Timeline:                                  │   │
│          │ │ ● Submitted → ● Evaluated → ● Awarded     │   │
│          │ ├────────────────────────────────────────────┤   │
│          │ │ Details:                                   │   │
│          │ │ Award Value: 50,00,000 BDT                 │   │
│          │ │ Contract Period: 12 months                 │   │
│          │ │ Performance Security: 5%                   │   │
│          │ ├────────────────────────────────────────────┤   │
│          │ │ Documents:                                 │   │
│          │ │ [Award Letter] [Contract] [Performance Sec]│   │
│          │ └────────────────────────────────────────────┘   │
├──────────┴──────────────────────────────────────────────────┤
│ AiDock (performance monitoring, milestone tracking)          │
└─────────────────────────────────────────────────────────────┘
```

## Component Tree

```
AwardPage
├── ExecutiveHeader
├── Breadcrumb
├── AwardHeader
│   ├── Badge (status)
│   └── KpiStrip (award_value, contract_period, performance_security)
├── AwardTracker
│   ├── Timeline
│   │   └── TimelineItem × N
│   │       ├── icon
│   │       ├── title
│   │       ├── date
│   │       └── description
│   ├── AwardDetails
│   │   ├── KpiCard (award_value)
│   │   ├── KpiCard (contract_period)
│   │   ├── KpiCard (performance_security)
│   │   └── KpiCard (milestone_progress)
│   └── DocumentList
│       └── DocumentCard × N
│           ├── DocumentViewer
│           └── Button (Download)
└── AiDock
    ├── AgentCard (Decision Agent)
    └── EvidencePanel (performance insights)
```

## Data Sources

### Award Details
```typescript
// API: GET /api/v1/awards/{award_id}
interface AwardDetails {
  award_id: string;
  tender_id: string;
  title: string;
  agency: string;
  award_value: number;
  contract_period: number;
  performance_security_pct: number;
  status: 'submitted' | 'evaluated' | 'awarded' | 'in_progress' | 'completed';
  awarded_at: string;
  documents: AwardDocument[];
  milestones: Milestone[];
}

interface AwardDocument {
  document_id: string;
  type: string;
  name: string;
  url: string;
  uploaded_at: string;
}

interface Milestone {
  milestone_id: string;
  title: string;
  due_date: string;
  completion_pct: number;
  status: 'pending' | 'in_progress' | 'completed' | 'delayed';
}
```

### React Query
```typescript
const { data: award } = useQuery({
  queryKey: ['awards', awardId],
  queryFn: () => api.get(`/api/v1/awards/${awardId}`),
});

const updateMilestone = useMutation({
  mutationFn: ({ milestoneId, updates }: { milestoneId: string; updates: Partial<Milestone> }) =>
    api.patch(`/api/v1/awards/${awardId}/milestones/${milestoneId}`, updates),
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ['awards', awardId] });
  },
});
```

## Zustand Store
```typescript
// stores/awardStore.ts
interface AwardState {
  activeTab: 'timeline' | 'details' | 'documents' | 'milestones';
  selectedMilestone: string | null;
  setActiveTab: (tab: string) => void;
  setSelectedMilestone: (id: string | null) => void;
}
```

## Interactions

### Timeline Navigation
1. Click timeline item
2. Highlight corresponding milestone
3. Show details in drawer
4. View related documents

### Milestone Management
1. Click milestone card
2. Update progress percentage
3. Add notes/comments
4. Upload supporting documents

### Document Management
1. Click document card
2. Open DocumentViewer
3. Download document
4. Add annotations

### Status Updates
1. Click status badge
2. Open status change modal
3. Select new status
4. Add transition notes

## Responsive Breakpoints

| Breakpoint | Layout |
|------------|--------|
| Desktop (>1024px) | Full timeline + details |
| Tablet (768-1024px) | Collapsible timeline |
| Mobile (<768px) | Stacked cards, bottom tabs |

## Loading States
- Timeline: Skeleton items
- Details: Skeleton cards
- Documents: Skeleton list

## Error States
- Award not found: 404 page
- Document load failure: Retry button
- API error: Toast notification

## Accessibility
- Timeline items are focusable
- Status changes announced via `aria-live`
- Screen reader: "Milestone X, status: in_progress"
- Keyboard: Enter to select, Arrow keys to navigate

## Telemetry
- `award.view` — Screen loaded
- `award.milestone_update` — Milestone updated
- `award.document_view` — Document viewed
- `award.status_change` — Status changed

## Implementation Notes
- Timeline shows award progression
- Milestone tracking with progress updates
- Document management with viewer
- AiDock provides performance insights
- Export generates award report
