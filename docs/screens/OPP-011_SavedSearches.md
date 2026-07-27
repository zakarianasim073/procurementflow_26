# OPP-011: Saved Searches Screen Specification

**Module:** `features/saved-searches/SavedSearchesPage`
**Layer:** features
**Version:** 1.0.0
**Status:** Draft
**Workspace:** Opportunity

## Purpose
Manage saved search queries and automated alerts.

## Screen Layout

```
┌─────────────────────────────────────────────────────────────┐
│ ExecutiveHeader                                             │
├──────────┬──────────────────────────────────────────────────┤
│          │ Breadcrumb: Opportunity > Saved Searches          │
│ Workspace├──────────────────────────────────────────────────┤
│   Nav    │ SavedSearchesHeader (count, alerts)              │
│          ├──────────────────────────────────────────────────┤
│          │ SavedSearches (main content)                     │
│          │ ┌────────────────────────────────────────────┐   │
│          │ │ SearchList (saved searches)                 │   │
│          │ │ ┌──────────────────────────────────────────┐│   │
│          │ │ │ Search: "BWDB tenders"  [Alert: ON]     ││   │
│          │ │ │ Search: "High value"    [Alert: OFF]    ││   │
│          │ │ │ ...                                      ││   │
│          │ │ └──────────────────────────────────────────┘│   │
│          │ ├────────────────────────────────────────────┤   │
│          │ │ SearchDetails (selected search)             │   │
│          │ └────────────────────────────────────────────┘   │
├──────────┴──────────────────────────────────────────────────┤
│ AiDock (search insights)                                    │
└─────────────────────────────────────────────────────────────┘
```

## Component Tree

```
SavedSearchesPage
├── ExecutiveHeader
├── Breadcrumb
├── SavedSearchesHeader
│   ├── KpiStrip (search_count, alert_count)
│   └── Button (New Search)
├── SavedSearches
│   ├── SearchList
│   │   └── SearchCard × N
│   │       ├── name
│   │       ├── query
│   │       ├── filters
│   │       ├── alert_enabled
│   │       ├── last_run
│   │       └── actions (run, edit, delete)
│   ├── SearchDetails
│   │   ├── query_info
│   │   ├── filter_summary
│   │   ├── results_preview
│   │   └── alert_settings
│   ├── AlertHistory
│   │   └── AlertEntry × N
│   │       ├── date
│   │       ├── results_count
│   │       └── new_tenders
│   └── SearchAnalytics
│       ├── search_frequency
│       ├── results_trend
│       └── alert_effectiveness
└── AiDock
    ├── AgentCard (Search Agent)
    └── EvidencePanel (search insights)
```

## Data Sources

### Saved Searches
```typescript
// API: GET /api/v1/opportunities/searches
interface SavedSearchList {
  searches: SavedSearch[];
  total_count: number;
  alert_count: number;
}

interface SavedSearch {
  search_id: string;
  name: string;
  query: string;
  filters: Record<string, any>;
  alert_enabled: boolean;
  alert_frequency: string;
  last_run: string;
  last_results_count: number;
  created_at: string;
}
```

### React Query
```typescript
const { data: searches } = useQuery({
  queryKey: ['opportunities', 'searches'],
  queryFn: () => api.get('/api/v1/opportunities/searches'),
});

const runSearch = useMutation({
  mutationFn: (searchId: string) => api.post(`/api/v1/opportunities/searches/${searchId}/run`),
  onSuccess: (data) => {
    toast.success(`Found ${data.results_count} results`);
  },
});

const toggleAlert = useMutation({
  mutationFn: ({ searchId, enabled }: { searchId: string; enabled: boolean }) =>
    api.patch(`/api/v1/opportunities/searches/${searchId}`, { alert_enabled: enabled }),
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ['opportunities', 'searches'] });
    toast.success('Alert updated');
  },
});
```

## Zustand Store
```typescript
// stores/savedSearchesStore.ts
interface SavedSearchesState {
  selectedSearch: string | null;
  setSearch: (id: string | null) => void;
}
```

## Interactions

### Run Search
1. Click Run button
2. Execute search
3. View results
4. Update last_run

### Toggle Alert
1. Click alert toggle
2. Update setting
3. Confirm change
4. Refresh list

### Edit Search
1. Click Edit button
2. Modify query/filters
3. Save changes
4. Update card

### View Results
1. Click search card
2. Preview results
3. Open full results
4. Apply to current view

## Responsive Breakpoints

| Breakpoint | Layout |
|------------|--------|
| Desktop (>1024px) | Full list + details |
| Tablet (768-1024px) | List with modal details |
| Mobile (<768px) | Simplified list |

## Loading States
- Searches: Skeleton cards
- Details: Loading spinner
- Results: Loading animation

## Error States
- Run failure: Toast error
- Save failure: Toast error
- Network error: Toast notification

## Accessibility
- Searches are focusable
- Alert status announced via `aria-live`
- Screen reader: "Search: BWDB tenders, alert: on"
- Keyboard: Tab through searches

## Telemetry
- `saved_searches.view` — Screen loaded
- `saved_searches.run` — Search run
- `saved_searches.alert_toggle` — Alert toggled
- `saved_searches.edit` — Search edited
- `saved_searches.delete` — Search deleted

## Implementation Notes
- Saved search management
- Alert system
- Search analytics
- AiDock provides search insights
- Export results
