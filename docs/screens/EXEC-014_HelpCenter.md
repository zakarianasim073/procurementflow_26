# EXEC-014: Help Center Screen Specification

**Module:** `features/help-center/HelpCenterPage`
**Layer:** features
**Version:** 1.0.0
**Status:** Draft
**Workspace:** Dashboard

## Purpose
User help, documentation, tutorials, and support resources.

## Screen Layout

```
┌─────────────────────────────────────────────────────────────┐
│ ExecutiveHeader                                             │
├──────────┬──────────────────────────────────────────────────┤
│          │ Breadcrumb: Dashboard > Help Center               │
│ Workspace├──────────────────────────────────────────────────┤
│   Nav    │ HelpCenterHeader (search, categories)            │
│          ├──────────────────────────────────────────────────┤
│          │ HelpCenter (main content)                        │
│          │ ┌────────────────────────────────────────────┐   │
│          │ │ SearchBar (help search)                     │   │
│          │ ├────────────────────────────────────────────┤   │
│          │ │ CategoryGrid (help categories)              │   │
│          │ │ ┌──────┬──────┬──────┬──────┐              │   │
│          │ │ │Getting│Tenders│BOQ  │Pricing│              │   │
│          │ │ │Started│       │      │      │              │   │
│          │ │ ├──────┼──────┼──────┼──────┤              │   │
│          │ │ │Admin │Trust │Know │Help  │              │   │
│          │ │ │      │      │ledge │Desk  │              │   │
│          │ │ └──────┴──────┴──────┴──────┘              │   │
│          │ ├────────────────────────────────────────────┤   │
│          │ │ PopularArticles (trending)                   │   │
│          │ └────────────────────────────────────────────┘   │
├──────────┴──────────────────────────────────────────────────┤
│ AiDock (help suggestions)                                   │
└─────────────────────────────────────────────────────────────┘
```

## Component Tree

```
HelpCenterPage
├── ExecutiveHeader
├── Breadcrumb
├── HelpCenterHeader
│   ├── SearchBar (help search)
│   └── ChipSelect (categories)
├── HelpCenter
│   ├── SearchResults
│   │   └── ArticleCard × N
│   │       ├── title
│   │       ├── excerpt
│   │       ├── category
│   │       └── read_time
│   ├── CategoryGrid
│   │   └── CategoryCard × N
│   │       ├── icon
│   │       ├── name
│   │       ├── article_count
│   │       └── Button (Browse)
│   ├── PopularArticles
│   │   └── ArticleList
│   │       └── ArticleCard × N
│   │           ├── title
│   │           ├── views
│   │           ├── helpful_count
│   │           └── Button (Read)
│   └── QuickLinks
│       ├── Getting Started
│       ├── FAQs
│       ├── Tutorials
│       └── Contact Support
└── AiDock
    ├── AgentCard (Help Agent)
    └── EvidencePanel (help suggestions)
```

## Data Sources

### Help Articles
```typescript
// API: GET /api/v1/help/articles
interface HelpArticleList {
  articles: HelpArticle[];
  total_count: number;
}

interface HelpArticle {
  article_id: string;
  title: string;
  content: string;
  category: string;
  tags: string[];
  read_time: number;
  views: number;
  helpful_count: number;
  created_at: string;
  updated_at: string;
}
```

### Help Categories
```typescript
// API: GET /api/v1/help/categories
interface HelpCategory {
  category_id: string;
  name: string;
  description: string;
  icon: string;
  article_count: number;
}
```

### React Query
```typescript
const { data: articles } = useQuery({
  queryKey: ['help', 'articles', filters],
  queryFn: () => api.get('/api/v1/help/articles', { params: filters }),
});

const { data: categories } = useQuery({
  queryKey: ['help', 'categories'],
  queryFn: () => api.get('/api/v1/help/categories'),
});
```

## Zustand Store
```typescript
// stores/helpCenterStore.ts
interface HelpCenterState {
  searchQuery: string;
  selectedCategory: string | null;
  setSearch: (query: string) => void;
  setCategory: (category: string | null) => void;
}
```

## Interactions

### Search Help
1. Type query
2. View results
3. Select article
4. Read content

### Browse Category
1. Click category card
2. View articles
3. Filter by topic
4. Read article

### Rate Article
1. Read article
2. Click Helpful/Not Helpful
3. Submit feedback
4. Update count

### Get Support
1. Click Contact Support
2. Submit ticket
3. Get response
4. Track status

## Responsive Breakpoints

| Breakpoint | Layout |
|------------|--------|
| Desktop (>1024px) | Full grid + popular |
| Tablet (768-1024px) | Stacked grid |
| Mobile (<768px) | Simplified list |

## Loading States
- Articles: Skeleton cards
- Categories: Skeleton grid
- Search: Loading spinner

## Error States
- Search failure: Retry button
- No results: EmptyState
- Network error: Toast notification

## Accessibility
- Articles are focusable
- Results announced via `aria-live`
- Screen reader: "Article: Getting Started"
- Keyboard: Tab through articles

## Telemetry
- `help_center.view` — Screen loaded
- `help_center.search` — Search performed
- `help_center.article_read` — Article read
- `help_center.category_browse` — Category browsed

## Implementation Notes
- Full-text search
- Category organization
- Article rating
- AiDock provides help suggestions
- Contact support integration
