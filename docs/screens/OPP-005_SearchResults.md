# OPP-005: Search Results Screen Specification

**Module:** `features/search/SearchResultsPage`
**Layer:** features
**Version:** 1.0.0
**Status:** Draft
**Workspace:** Discovery

## Purpose
Global search across tenders, contractors, and knowledge base with advanced filtering.

## Screen Layout

```
┌─────────────────────────────────────────────────────────────┐
│ ExecutiveHeader                                             │
├──────────┬──────────────────────────────────────────────────┤
│          │ Breadcrumb: Discovery > Search Results            │
│ Workspace├──────────────────────────────────────────────────┤
│   Nav    │ SearchResultsHeader (query, filters)             │
│          ├──────────────────────────────────────────────────┤
│          │ SearchResults (main content)                     │
│          │ ┌────────────────────────────────────────────┐   │
│          │ │ SearchBar (prominent, autocomplete)         │   │
│          │ ├────────────────────────────────────────────┤   │
│          │ │ FilterPanel (type, agency, zone, date)      │   │
│          │ ├────────────────────────────────────────────┤   │
│          │ │ ResultsList (grouped by type)               │   │
│          │ │ ┌──────────────────────────────────────────┐│   │
│          │ │ │ Tenders (5 results)                      ││   │
│          │ │ │ Contractors (3 results)                  ││   │
│          │ │ │ Knowledge (2 results)                    ││   │
│          │ │ └──────────────────────────────────────────┘│   │
│          │ └────────────────────────────────────────────┘   │
├──────────┴──────────────────────────────────────────────────┤
│ AiDock (search suggestions, related queries)                │
└─────────────────────────────────────────────────────────────┘
```

## Component Tree

```
SearchResultsPage
├── ExecutiveHeader
├── Breadcrumb
├── SearchResultsHeader
│   ├── SearchBar (prominent, autocomplete)
│   └── FilterPanel
│       ├── ChipSelect (type: tender/contractor/knowledge)
│       ├── ChipSelect (agencies)
│       ├── ChipSelect (zones)
│       └── CalendarRange (date range)
├── SearchResults
│   ├── ResultsSummary
│   │   ├── total_count
│   │   └── facets (type breakdown)
│   ├── ResultsList
│   │   ├── ResultGroup × N
│   │   │   ├── group_name (Tenders, Contractors, etc.)
│   │   │   └── ResultItem × N
│   │   │       ├── icon
│   │   │       ├── title
│   │   │       ├── excerpt (highlighted)
│   │   │       ├── metadata
│   │   │       └── relevance_score
│   │   └── Pagination
│   └── NoResults
│       ├── suggestions
│       └── related_queries
└── AiDock
    ├── AgentCard (Search Agent)
    └── EvidencePanel (search suggestions)
```

## Data Sources

### Search
```typescript
// API: POST /api/v1/search
interface SearchRequest {
  query: string;
  types?: string[];
  agencies?: string[];
  zones?: string[];
  date_range?: { start: string; end: string };
  page?: number;
  size?: number;
}

interface SearchResponse {
  items: SearchResult[];
  total_count: number;
  facets: SearchFacet[];
  suggestions: string[];
}

interface SearchResult {
  id: string;
  type: 'tender' | 'contractor' | 'knowledge';
  title: string;
  excerpt: string;
  metadata: Record<string, any>;
  relevance_score: number;
  url: string;
}

interface SearchFacet {
  type: string;
  count: number;
}
```

### React Query
```typescript
const { data: results } = useQuery({
  queryKey: ['search', query, filters],
  queryFn: () => api.post('/api/v1/search', { query, ...filters }),
  enabled: !!query,
});
```

## Zustand Store
```typescript
// stores/searchResultsStore.ts
interface SearchResultsState {
  query: string;
  filters: SearchRequest;
  setPage: (page: number) => void;
  setFilter: <K extends keyof SearchRequest>(key: K, value: SearchRequest[K]) => void;
  setQuery: (query: string) => void;
}
```

## Interactions

### Search
1. Type in search bar
2. Debounce 300ms
3. Update results
4. Show facets

### Filter Results
1. Apply filter
2. Refetch results
3. Update facets
4. Preserve query

### View Result
1. Click result item
2. Navigate to detail page
3. Track click
4. Update analytics

### Refine Search
1. View suggestions
2. Click suggestion
3. Update query
4. Refresh results

## Responsive Breakpoints

| Breakpoint | Layout |
|------------|--------|
| Desktop (>1024px) | Full results with facets |
| Tablet (768-1024px) | Stacked filters |
| Mobile (<768px) | Single column, bottom filters |

## Loading States
- Results: Skeleton cards
- Facets: Skeleton counts
- Autocomplete: Loading spinner

## Error States
- Search failure: Retry button
- No results: Suggestions
- Network error: Toast notification

## Accessibility
- Results are focusable
- Count announced via `aria-live`
- Screen reader: "Result X of Y"
- Keyboard: Arrow keys to navigate, Enter to select

## Telemetry
- `search.view` — Screen loaded
- `search.query` — Search performed
- `search.filter` — Filter applied
- `search.result_click` — Result clicked

## Implementation Notes
- Prominent search bar with autocomplete
- Faceted search with type breakdown
- Highlighted excerpts
- AiDock provides search suggestions
- Export for analysis
