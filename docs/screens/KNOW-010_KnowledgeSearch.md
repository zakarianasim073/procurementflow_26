# KNOW-010: Knowledge Search Screen Specification

**Module:** `features/knowledge-search/KnowledgeSearchPage`
**Layer:** features
**Version:** 1.0.0
**Status:** Draft
**Workspace:** Knowledge

## Purpose
Full-text search across knowledge base, documents, and tender data.

## Screen Layout

```
┌─────────────────────────────────────────────────────────────┐
│ ExecutiveHeader                                             │
├──────────┬──────────────────────────────────────────────────┤
│          │ Breadcrumb: Knowledge > Knowledge Search          │
│ Workspace├──────────────────────────────────────────────────┤
│   Nav    │ KnowledgeSearchHeader (search, filters)          │
│          ├──────────────────────────────────────────────────┤
│          │ KnowledgeSearch (main content)                   │
│          │ ┌────────────────────────────────────────────┐   │
│          │ │ SearchBar (prominent, autocomplete)         │   │
│          │ ├────────────────────────────────────────────┤   │
│          │ │ FilterPanel (type, category, date)          │   │
│          │ ├────────────────────────────────────────────┤   │
│          │ │ ResultsList (grouped by type)               │   │
│          │ │ ┌──────────────────────────────────────────┐│   │
│          │ │ │ Documents (5 results)                    ││   │
│          │ │ │ Entries (3 results)                      ││   │
│          │ │ │ Tenders (2 results)                      ││   │
│          │ │ └──────────────────────────────────────────┘│   │
│          │ └────────────────────────────────────────────┘   │
├──────────┴──────────────────────────────────────────────────┤
│ AiDock (search suggestions, related queries)                │
└─────────────────────────────────────────────────────────────┘
```

## Component Tree

```
KnowledgeSearchPage
├── ExecutiveHeader
├── Breadcrumb
├── KnowledgeSearchHeader
│   ├── SearchBar (prominent, autocomplete)
│   └── FilterPanel
│       ├── ChipSelect (type: document/entry/tender)
│       ├── ChipSelect (categories)
│       └── CalendarRange (date range)
├── KnowledgeSearch
│   ├── ResultsSummary
│   │   ├── total_count
│   │   └── facets (type breakdown)
│   ├── ResultsList
│   │   ├── ResultGroup × N
│   │   │   ├── group_name (Documents, Entries, etc.)
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
    ├── AgentCard (Knowledge Agent)
    └── EvidencePanel (search suggestions)
```

## Data Sources

### Search
```typescript
// API: POST /api/v1/knowledge/search
interface SearchRequest {
  query: string;
  types?: string[];
  categories?: string[];
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
  type: 'document' | 'entry' | 'tender';
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
  queryKey: ['knowledge', 'search', query, filters],
  queryFn: () => api.post('/api/v1/knowledge/search', { query, ...filters }),
  enabled: !!query,
});
```

## Zustand Store
```typescript
// stores/knowledgeSearchStore.ts
interface KnowledgeSearchState {
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
- `knowledge_search.view` — Screen loaded
- `knowledge_search.query` — Search performed
- `knowledge_search.filter` — Filter applied
- `knowledge_search.result_click` — Result clicked

## Implementation Notes
- Prominent search bar with autocomplete
- Faceted search with type breakdown
- Highlighted excerpts
- AiDock provides search suggestions
- Export for analysis
