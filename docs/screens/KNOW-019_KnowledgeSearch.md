# KNOW-019: Knowledge Search Screen Specification

**Module:** `features/knowledge-search/KnowledgeSearchPage`
**Layer:** features
**Version:** 1.0.0
**Status:** Draft
**Workspace:** Knowledge

## Purpose
Advanced knowledge base search with filters, facets, and intelligent ranking.

## Screen Layout

```
┌─────────────────────────────────────────────────────────────┐
│ ExecutiveHeader                                             │
├──────────┬──────────────────────────────────────────────────┤
│          │ Breadcrumb: Knowledge > Knowledge Search          │
│ Workspace├──────────────────────────────────────────────────┤
│   Nav    │ KnowledgeSearchHeader (query, results)           │
│          ├──────────────────────────────────────────────────┤
│          │ KnowledgeSearch (main content)                   │
│          │ ┌────────────────────────────────────────────┐   │
│          │ │ SearchBar (main search)                     │   │
│          │ ├────────────────────────────────────────────┤   │
│          │ │ FilterPanel (facets, filters)               │   │
│          │ ├────────────────────────────────────────────┤   │
│          │ │ ResultsList (search results)                │   │
│          │ │ ┌──────────────────────────────────────────┐│   │
│          │ │ │ Result 1: "BOQ Analysis Guide"           ││   │
│          │ │ │ Result 2: "SOR Rate Comparison"          ││   │
│          │ │ │ ...                                      ││   │
│          │ │ └──────────────────────────────────────────┘│   │
│          │ ├────────────────────────────────────────────┤   │
│          │ │ ResultPreview (selected result)             │   │
│          │ └────────────────────────────────────────────┘   │
├──────────┴──────────────────────────────────────────────────┤
│ AiDock (search suggestions)                                 │
└─────────────────────────────────────────────────────────────┘
```

## Component Tree

```
KnowledgeSearchPage
├── ExecutiveHeader
├── Breadcrumb
├── KnowledgeSearchHeader
│   ├── SearchBar (main search)
│   ├── KpiStrip (result_count, search_time)
│   └── Button (Advanced Search)
├── KnowledgeSearch
│   ├── FilterPanel
│   │   ├── ChipSelect (content_type)
│   │   ├── ChipSelect (category)
│   │   ├── ChipSelect (date_range)
│   │   └── ChipSelect (relevance)
│   ├── ResultsList
│   │   └── VirtualList<SearchResult>
│   │       └── ResultCard × N
│   │           ├── title
│   │           ├── excerpt
│   │           ├── source
│   │           ├── relevance_score
│   │           └── Button (View)
│   ├── ResultPreview
│   │   ├── content
│   │   ├── metadata
│   │   └── related_results
│   └── SearchSuggestions
│       └── Suggestion × N
│           ├── query
│           └── Button (Search)
└── AiDock
    ├── AgentCard (Search Agent)
    └── EvidencePanel (search suggestions)
```

## Data Sources

### Knowledge Search
```typescript
// API: GET /api/v1/knowledge/search
interface KnowledgeSearch {
  results: SearchResult[];
  total_count: number;
  search_time: number;
  suggestions: string[];
}

interface SearchResult {
  result_id: string;
  title: string;
  excerpt: string;
  content: string;
  source: string;
  category: string;
  content_type: string;
  relevance_score: number;
  created_at: string;
  updated_at: string;
}
```

### React Query
```typescript
const { data: searchResults } = useQuery({
  queryKey: ['knowledge', 'search', query, filters],
  queryFn: () => api.get('/api/v1/knowledge/search', { params: { query, ...filters } }),
  enabled: !!query,
});
```

## Zustand Store
```typescript
// stores/knowledgeSearchStore.ts
interface KnowledgeSearchState {
  query: string;
  filters: {
    content_type: string[];
    category: string[];
    date_range: { start: string; end: string } | null;
  };
  setQuery: (query: string) => void;
  setFilter: <K extends keyof KnowledgeSearchState['filters']>(key: K, value: KnowledgeSearchState['filters'][K]) => void;
}
```

## Interactions

### Search Knowledge
1. Type query
2. Execute search
3. View results
4. Preview content

### Apply Filters
1. Select filters
2. Update results
3. Preserve query
4. Refresh display

### View Result
1. Click result card
2. Preview content
3. Read details
4. View source

### Use Suggestion
1. Click suggestion
2. Update query
3. Execute search
4. View results

## Responsive Breakpoints

| Breakpoint | Layout |
|------------|--------|
| Desktop (>1024px) | Full search + results |
| Tablet (768-1024px) | Search with collapsible filters |
| Mobile (<768px) | Simplified search |

## Loading States
- Search: Loading results
- Preview: Loading content
- Filters: Loading facets

## Error States
- Search failure: Retry button
- No results: EmptyState
- Network error: Toast notification

## Accessibility
- Results are focusable
- Count announced via `aria-live`
- Screen reader: "Result 1 of 50: BOQ Analysis Guide"
- Keyboard: Arrow keys to navigate

## Telemetry
- `knowledge_search.view` — Screen loaded
- `knowledge_search.query` — Search performed
- `knowledge_search.filter` — Filter applied
- `knowledge_search.result_view` — Result viewed

## Implementation Notes
- Full-text search
- Faceted filtering
- Relevance ranking
- AiDock provides search suggestions
- Result preview
