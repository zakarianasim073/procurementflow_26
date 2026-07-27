# OPP-001: Tender Discovery Screen Specification

**Module:** `features/discovery/DiscoveryPage`
**Layer:** features
**Version:** 1.0.0
**Status:** Draft
**Workspace:** Discovery

## Purpose
AI-powered tender discovery and filtering from 395K+ tenders, with smart matching, bulk operations, and pipeline progression.

## Screen Layout

```
┌─────────────────────────────────────────────────────────────┐
│ ExecutiveHeader                                             │
├──────────┬──────────────────────────────────────────────────┤
│          │ FilterPanel (multi-select, search, date range)   │
│ Workspace├──────────────────────────────────────────────────┤
│   Nav    │ ResultsHeader (count, sort, view toggle)         │
│          ├──────────────────────────────────────────────────┤
│          │ TenderList (virtualized, selectable rows)        │
│          │ ┌────────────────────────────────────────────┐   │
│          │ │ TenderCard × N (icon, title, agency, date) │   │
│          │ │ [checkbox] Title          Agency   Status  │   │
│          │ │ [checkbox] Title          Agency   Status  │   │
│          │ │ ...                                        │   │
│          │ └────────────────────────────────────────────┘   │
│          ├──────────────────────────────────────────────────┤
│          │ BulkActionBar (select all, pipeline actions)     │
├──────────┴──────────────────────────────────────────────────┤
│ AiDock (AI suggestions, auto-qualify, bulk analyze)         │
└─────────────────────────────────────────────────────────────┘
```

## Component Tree

```
DiscoveryPage
├── ExecutiveHeader
├── FilterPanel
│   ├── ChipSelect (agencies: BWDB, PWD, LGED)
│   ├── ChipSelect (zones: A, B, C, D)
│   ├── ChipSelect (status: Live, Archive, Cancel)
│   ├── CalendarRange (submission deadline)
│   ├── RangeSlider (estimated value)
│   └── SearchBar (keyword search)
├── ResultsHeader
│   ├── TenderCard (count badge)
│   ├── SortDropdown (date, value, probability)
│   └── ViewToggle (list/grid)
├── VirtualList<TenderCard>
│   └── TenderCard × N
├── BulkActionBar
│   ├── Button (Move to Qualification)
│   ├── Button (Run AI Analysis)
│   └── Button (Export Selection)
└── AiDock
    ├── AgentCard (Discovery Agent)
    └── EvidencePanel (recommendations)
```

## Data Sources

### Tender Search
```typescript
// API: POST /api/v1/tenders/search
interface TenderSearchRequest {
  keyword?: string;
  agencies?: string[];
  zones?: string[];
  status?: 'Live' | 'Archive' | 'Cancel';
  min_value?: number;
  max_value?: number;
  deadline_from?: string;
  deadline_to?: string;
  page: number;
  size: number;
  sort_by?: 'deadline' | 'value' | 'created_at';
  sort_order?: 'asc' | 'desc';
}

interface TenderSearchResponse {
  items: TenderSummary[];
  total: number;
  page: number;
  size: number;
}

interface TenderSummary {
  tender_id: string;
  title: string;
  agency: string;
  zone: string;
  estimated_value: number;
  submission_deadline: string;
  status: 'Live' | 'Archive' | 'Cancel';
  win_probability?: number;
  ai_match_score?: number;
}
```

### React Query
```typescript
const { data, isLoading, fetchNextPage } = useInfiniteQuery({
  queryKey: ['tenders', 'search', filters],
  queryFn: ({ pageParam }) => api.post('/api/v1/tenders/search', { ...filters, page: pageParam }),
  getNextPageParam: (lastPage) => lastPage.items.length === lastPage.size ? lastPage.page + 1 : undefined,
  initialPageParam: 1,
});
```

## Zustand Store
```typescript
// stores/discoveryStore.ts
interface DiscoveryState {
  filters: TenderSearchRequest;
  selectedTenders: Set<string>;
  viewMode: 'list' | 'grid';
  setFilter: <K extends keyof TenderSearchRequest>(key: K, value: TenderSearchRequest[K]) => void;
  toggleSelect: (tenderId: string) => void;
  selectAll: (tenderIds: string[]) => void;
  clearSelection: () => void;
  setViewMode: (mode: 'list' | 'grid') => void;
}
```

## Interactions

### Filter Change
1. Update Zustand store
2. Debounce 300ms
3. Reset pagination to page 1
4. Refetch tender search

### Tender Card Click
1. Navigate to `/discovery/{tender_id}`
2. Open Drawer with tender details
3. Show tabs: Overview, Documents, AI Analysis

### Bulk Select
1. Click checkbox to toggle selection
2. Shift+Click for range select
3. BulkActionBar appears when selection > 0
4. Actions: Move to Qualification, Run AI, Export

### Move to Qualification
1. POST `/api/v1/tenders/{id}/qualify`
2. Tender moves to OPP-002
3. Toast: "Tender moved to Qualification"
4. Remove from discovery list

## Responsive Breakpoints

| Breakpoint | Layout |
|------------|--------|
| Desktop (>1024px) | Sidebar filters + full list |
| Tablet (768-1024px) | Top filter bar + list |
| Mobile (<768px) | Bottom sheet filters + list |

## Loading States
- FilterPanel: Skeleton chips
- Results: 10 skeleton TenderCards
- Infinite scroll spinner at bottom

## Error States
- Network error: Retry button + error message
- No results: EmptyState with search tips
- API error: Toast notification

## Accessibility
- Filter changes announced via `aria-live="polite"`
- Keyboard: Ctrl+A select all, Delete remove
- Screen reader: "X tenders found, Y selected"
- Focus management between filter and list

## Telemetry
- `discovery.view` — Screen loaded
- `discovery.filter` — Filter changed (type, value)
- `discovery.select` — Tender selected
- `discovery.bulk_action` — Bulk action triggered
- `discovery.navigate` — Tender clicked

## Implementation Notes
- Uses VirtualList for 100K+ tender performance
- FilterPanel is collapsible on tablet/mobile
- AiDock provides contextual AI suggestions
- Infinite scroll pagination via React Query
