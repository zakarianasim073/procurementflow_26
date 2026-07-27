# KNOW-021: Knowledge Base Screen Specification

**Module:** `features/knowledge-base/KnowledgeBasePage`
**Layer:** features
**Version:** 1.0.0
**Status:** Draft
**Workspace:** Knowledge

## Purpose
Centralized knowledge base with articles, guides, and documentation.

## Screen Layout

```
┌─────────────────────────────────────────────────────────────┐
│ ExecutiveHeader                                             │
├──────────┬──────────────────────────────────────────────────┤
│          │ Breadcrumb: Knowledge > Knowledge Base            │
│ Workspace├──────────────────────────────────────────────────┤
│   Nav    │ KnowledgeBaseHeader (articles, categories)       │
│          ├──────────────────────────────────────────────────┤
│          │ KnowledgeBase (main content)                     │
│          │ ┌────────────────────────────────────────────┐   │
│          │ │ SearchBar (article search)                  │   │
│          │ ├────────────────────────────────────────────┤   │
│          │ │ CategoryTree (knowledge categories)         │   │
│          │ ├────────────────────────────────────────────┤   │
│          │ │ ArticleList (articles)                      │   │
│          │ │ ┌──────────────────────────────────────────┐│   │
│          │ │ │ Article: "BOQ Analysis Guide"            ││   │
│          │ │ │ Article: "SOR Rate Comparison"           ││   │
│          │ │ │ ...                                      ││   │
│          │ │ └──────────────────────────────────────────┘│   │
│          │ ├────────────────────────────────────────────┤   │
│          │ │ ArticleView (selected article)              │   │
│          │ └────────────────────────────────────────────┘   │
├──────────┴──────────────────────────────────────────────────┤
│ AiDock (knowledge suggestions)                              │
└─────────────────────────────────────────────────────────────┘
```

## Component Tree

```
KnowledgeBasePage
├── ExecutiveHeader
├── Breadcrumb
├── KnowledgeBaseHeader
│   ├── KpiStrip (article_count, category_count)
│   └── Button (Create Article)
├── KnowledgeBase
│   ├── SearchBar
│   │   └── SearchInput
│   ├── CategoryTree
│   │   └── Category × N
│   │       ├── name
│   │       ├── count
│   │       ├── expanded
│   │       └── children
│   ├── ArticleList
│   │   └── ArticleCard × N
│   │       ├── title
│   │       ├── excerpt
│   │       ├── category
│   │       ├── author
│   │       ├── updated_at
│   │       └── Button (Read)
│   ├── ArticleView
│   │   ├── article_content
│   │   ├── metadata
│   │   ├── related_articles
│   │   └── comments
│   └── KnowledgeStats
│       ├── chart (articles_by_category)
│       ├── chart (popular_articles)
│       └── chart (recent_updates)
└── AiDock
    ├── AgentCard (Knowledge Agent)
    └── EvidencePanel (knowledge suggestions)
```

## Data Sources

### Knowledge Base
```typescript
// API: GET /api/v1/knowledge/base
interface KnowledgeBase {
  articles: Article[];
  categories: Category[];
  stats: KnowledgeStats;
}

interface Article {
  article_id: string;
  title: string;
  content: string;
  excerpt: string;
  category: string;
  tags: string[];
  author: string;
  created_at: string;
  updated_at: string;
  views: number;
  helpful_count: number;
}

interface Category {
  category_id: string;
  name: string;
  description: string;
  count: number;
  children: Category[];
}

interface KnowledgeStats {
  total_articles: number;
  total_categories: number;
  popular_articles: { article_id: string; title: string; views: number }[];
  recent_updates: { article_id: string; title: string; updated_at: string }[];
}
```

### React Query
```typescript
const { data: knowledge } = useQuery({
  queryKey: ['knowledge', 'base'],
  queryFn: () => api.get('/api/v1/knowledge/base'),
});

const { data: article } = useQuery({
  queryKey: ['knowledge', 'base', articleId],
  queryFn: () => api.get(`/api/v1/knowledge/base/${articleId}`),
  enabled: !!articleId,
});

const createArticle = useMutation({
  mutationFn: (article: CreateArticleRequest) => api.post('/api/v1/knowledge/base', article),
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ['knowledge', 'base'] });
    toast.success('Article created');
  },
});
```

## Zustand Store
```typescript
// stores/knowledgeBaseStore.ts
interface KnowledgeBaseState {
  selectedArticle: string | null;
  expandedCategories: string[];
  searchQuery: string;
  setArticle: (id: string | null) => void;
  toggleCategory: (id: string) => void;
  setSearch: (query: string) => void;
}
```

## Interactions

### Search Articles
1. Type query
2. Search articles
3. View results
4. Select article

### Browse Categories
1. Click category
2. Expand/collapse
3. View articles
4. Filter by category

### Read Article
1. Click article card
2. View content
3. Check metadata
4. Read comments

### Create Article
1. Click Create
2. Write content
3. Set category
4. Publish article

## Responsive Breakpoints

| Breakpoint | Layout |
|------------|--------|
| Desktop (>1024px) | Full tree + list + view |
| Tablet (768-1024px) | Collapsible tree |
| Mobile (<768px) | Simplified list |

## Loading States
- Articles: Skeleton cards
- Categories: Loading tree
- View: Loading content

## Error States
- Load failure: Retry button
- Create failure: Toast error
- Network error: Toast notification

## Accessibility
- Articles are focusable
- Count announced via `aria-live`
- Screen reader: "Article: BOQ Guide, category: Technical"
- Keyboard: Tab through articles

## Telemetry
- `knowledge_base.view` — Screen loaded
- `knowledge_base.search` — Search performed
- `knowledge_base.article_read` — Article read
- `knowledge_base.article_create` — Article created

## Implementation Notes
- Knowledge base management
- Category organization
- Article creation
- AiDock provides knowledge suggestions
- Search and filtering
