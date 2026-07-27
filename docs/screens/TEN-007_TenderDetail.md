# TEN-007: Tender Detail Screen Specification

**Module:** `features/tender/TenderDetailPage`
**Layer:** features
**Version:** 1.0.0
**Status:** Draft
**Workspace:** Acquisition

## Purpose
Comprehensive tender view with all related data, documents, AI analysis, and actions.

## Screen Layout

```
┌─────────────────────────────────────────────────────────────┐
│ ExecutiveHeader                                             │
├──────────┬──────────────────────────────────────────────────┤
│          │ Breadcrumb: Acquisition > Tender > {Tender}      │
│ Workspace├──────────────────────────────────────────────────┤
│   Nav    │ TenderDetailHeader (title, status, actions)      │
│          ├──────────────────────────────────────────────────┤
│          │ TenderDetail (main content)                      │
│          │ ┌────────────────────────────────────────────┐   │
│          │ │ Tabs: [Overview] [Documents] [BOQ] [AI]   │   │
│          │ ├────────────────────────────────────────────┤   │
│          │ │ Overview: KPIs, timeline, summary          │   │
│          │ │ Documents: DocumentViewer, file list       │   │
│          │ │ BOQ: BoqTable, rate analysis               │   │
│          │ │ AI: Analysis results, recommendations     │   │
│          │ └────────────────────────────────────────────┘   │
├──────────┴──────────────────────────────────────────────────┤
│ AiDock (contextual actions, quick analysis)                 │
└─────────────────────────────────────────────────────────────┘
```

## Component Tree

```
TenderDetailPage
├── ExecutiveHeader
├── Breadcrumb
├── TenderDetailHeader
│   ├── TenderCard (full)
│   ├── Badge (status)
│   ├── ConfidenceBadge (win_probability)
│   └── ButtonGroup (Edit, Analyze, Submit)
├── TenderDetail
│   ├── Tabs
│   │   ├── OverviewTab
│   │   │   ├── KpiStrip (value, deadline, agency, zone)
│   │   │   ├── Timeline (tender lifecycle)
│   │   │   └── SummaryPanel (AI summary)
│   │   ├── DocumentsTab
│   │   │   ├── DocumentList
│   │   │   │   └── DocumentCard × N
│   │   │   └── DocumentViewer
│   │   ├── BOQTab
│   │   │   ├── BoqTable
│   │   │   └── RateAnalysisTable
│   │   └── AITab
│   │       ├── AnalysisResults
│   │       ├── Recommendations
│   │       └── EvidencePanel
│   └── TenderSidebar
│       ├── QuickActions
│       ├── RelatedTenders
│       └── ActivityLog
└── AiDock
    ├── AgentCard (multiple agents)
    └── EvidencePanel (tender insights)
```

## Data Sources

### Tender Details
```typescript
// API: GET /api/v1/tenders/{tender_id}
interface TenderDetails {
  tender_id: string;
  title: string;
  agency: string;
  zone: string;
  estimated_value: number;
  submission_deadline: string;
  status: string;
  win_probability: number;
  created_at: string;
  updated_at: string;
  documents: Document[];
  boq_items: BoqItem[];
  ai_analysis?: AiAnalysis;
}
```

### React Query
```typescript
const { data: tender } = useQuery({
  queryKey: ['tenders', tenderId],
  queryFn: () => api.get(`/api/v1/tenders/${tenderId}`),
});

const { data: analysis } = useQuery({
  queryKey: ['tenders', tenderId, 'analysis'],
  queryFn: () => api.get(`/api/v1/tenders/${tenderId}/analysis`),
  enabled: !!tender,
});

const updateTender = useMutation({
  mutationFn: (request: UpdateTenderRequest) =>
    api.patch(`/api/v1/tenders/${tenderId}`, request),
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ['tenders', tenderId] });
    toast.success('Tender updated');
  },
});
```

## Zustand Store
```typescript
// stores/tenderDetailStore.ts
interface TenderDetailState {
  activeTab: string;
  sidebarOpen: boolean;
  setTab: (tab: string) => void;
  setSidebarOpen: (open: boolean) => void;
}
```

## Interactions

### Tab Switching
1. Click tab header
2. Update URL: `/tender/{id}?tab=overview`
3. Preserve scroll position
4. Lazy load tab content

### Document View
1. Click document in list
2. Open DocumentViewer
3. View content
4. Download or share

### Quick Action
1. Click action button
2. Execute action (analyze, qualify, etc.)
3. Show progress
4. Update tender status

### AI Analysis
1. Click AI tab
2. View analysis results
3. Read recommendations
4. Take suggested actions

## Responsive Breakpoints

| Breakpoint | Layout |
|------------|--------|
| Desktop (>1024px) | Full tabs + sidebar |
| Tablet (768-1024px) | Collapsible sidebar |
| Mobile (<768px) | Stacked tabs, bottom navigation |

## Loading States
- Tender: Skeleton card
- Documents: Skeleton list
- BOQ: Skeleton table
- AI: Loading spinner

## Error States
- Tender not found: 404 page
- Analysis failure: Retry button
- Network error: Toast notification

## Accessibility
- Tab navigation with arrow keys
- Content announced on tab switch
- Screen reader: "Tab X of Y"
- Keyboard: Enter to activate tab

## Telemetry
- `tender_detail.view` — Screen loaded
- `tender_detail.tab_switch` — Tab changed
- `tender_detail.document_view` — Document viewed
- `tender_detail.action` — Quick action executed

## Implementation Notes
- Comprehensive tender view
- 4 tabs with lazy loading
- DocumentViewer for preview
- AiDock provides contextual actions
- Sidebar with quick actions
