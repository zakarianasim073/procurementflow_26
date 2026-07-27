# KNOW-016: Search History Screen Specification

**Module:** `features/search-history/SearchHistoryPage`
**Layer:** features
**Version:** 1.0.0
**Status:** Draft
**Workspace:** Knowledge

## Purpose
Track and analyze search history, patterns, and effectiveness.

## Screen Layout

```
┌─────────────────────────────────────────────────────────────┐
│ ExecutiveHeader                                             │
├──────────┬──────────────────────────────────────────────────┤
│          │ Breadcrumb: Knowledge > Search History            │
│ Workspace├──────────────────────────────────────────────────┤
│   Nav    │ SearchHistoryHeader (count, patterns)            │
│          ├──────────────────────────────────────────────────┤
│          │ SearchHistory (main content)                     │
│          │ ┌────────────────────────────────────────────┐   │
│          │ │ SearchStats (overview)                      │   │
│          │ ├────────────────────────────────────────────┤   │
│          │ │ HistoryList (search entries)                │   │
│          │ │ ┌──────────────────────────────────────────┐│   │
│          │ │ │ Search: "BWDB tenders" at 10:00          ││   │
│          │ │ │ Search: "High value" at 10:05            ││   │
│          │ │ │ ...                                      ││   │
│          │ │ └──────────────────────────────────────────┘│   │
│          │ ├────────────────────────────────────────────┤   │
│          │ │ SearchPatterns (analytics)                  │   │
│          │ └────────────────────────────────────────────┘   │
├──────────┴──────────────────────────────────────────────────┤
│ AiDock (search insights)                                    │
└─────────────────────────────────────────────────────────────┘
```

## Component Tree

```
SearchHistoryPage
├── ExecutiveHeader
├── Breadcrumb
├── SearchHistoryHeader
│   ├── KpiStrip (search_count, unique_queries, avg_results)
│   └── Button (Clear History)
├── SearchHistory
│   ├── SearchStats
│   │   ├── Chart (search_frequency)
│   │   ├── Chart (top_queries)
│   │   └── Chart (search_times)
│   ├── HistoryList
│   │   └── VirtualList<SearchEntry>
│   │       └── SearchCard × N
│   │           ├── query
│   │           ├── timestamp
│   │           ├── results_count
│   │           ├── duration
│   │           └── Button (Rerun)
│   ├── SearchPatterns
│   │   ├── top_queries
│   │   ├── time_patterns
│   │   └── effectiveness
│   └── SearchInsights
│       ├── suggestions
│       ├── trends
│       └── recommendations
└── AiDock
    ├── AgentCard (Search Agent)
    └── EvidencePanel (search insights)
```

## Data Sources

### Search History
```typescript
// API: GET /api/v1/knowledge/search-history
interface SearchHistory {
  entries: SearchEntry[];
  total_count: number;
  unique_queries: number;
  avg_results: number;
}

interface SearchEntry {
  entry_id: string;
  query: string;
  filters: Record<string, any>;
  results_count: number;
  duration: number;
  timestamp: string;
  user_id: string;
}
```

### React Query
```typescript
const { data: history } = useQuery({
  queryKey: ['knowledge', 'search-history'],
  queryFn: () => api.get('/api/v1/knowledge/search-history'),
});

const rerunSearch = useMutation({
  mutationFn: (entryId: string) => api.post(`/api/v1/knowledge/search-history/${entryId}/rerun`),
  onSuccess: (data) => {
    toast.success(`Found ${data.results_count} results`);
  },
});

const clearHistory = useMutation({
  mutationFn: () => api.delete('/api/v1/knowledge/search-history'),
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ['knowledge', 'search-history'] });
    toast.success('History cleared');
  },
});
```

## Zustand Store
```typescript
// stores/searchHistoryStore.ts
interface SearchHistoryState {
  dateRange: { start: string; end: string } | null;
  setDateRange: (range: { start: string; end: string } | null) => void;
}
```

## Interactions

### Rerun Search
1. Click Rerun button
2. Execute search
3. View results
4. Update history

### Clear History
1. Click Clear button
2. Confirm clear
3. Remove entries
4. Update stats

### View Patterns
1. View analytics
2. Check trends
3. Read insights
4. Get recommendations

### Filter History
1. Set date range
2. Update list
3. Refresh stats
4. Update patterns

## Responsive Breakpoints

| Breakpoint | Layout |
|------------|--------|
| Desktop (>1024px) | Full stats + list |
| Tablet (768-1024px) | Stacked layout |
| Mobile (<768px) | Simplified list |

## Loading States
- History: Skeleton cards
- Stats: Loading charts
- Patterns: Loading analytics

## Error States
- Load failure: Retry button
- Clear failure: Toast error
- Network error: Toast notification

## Accessibility
- Entries are focusable
- Stats announced via `aria-live`
- Screen reader: "Search: BWDB tenders, 15 results"
- Keyboard: Arrow keys to navigate

## Telemetry
- `search_history.view` — Screen loaded
- `search_history.rerun` — Search rerun
- `search_history.clear` — History cleared
- `search_history.filter` — Filter applied

## Implementation Notes
- Search history tracking
- Pattern analysis
- Effectiveness metrics
- AiDock provides search insights
- Export for analysis
