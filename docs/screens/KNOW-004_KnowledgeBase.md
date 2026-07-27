# KNOW-004: Knowledge Base Screen Specification

**Module:** `features/knowledge/KnowledgeBasePage`
**Layer:** features
**Version:** 1.0.0
**Status:** Draft
**Workspace:** Knowledge

## Purpose
Centralized knowledge repository for tender documents, market intelligence, and institutional knowledge management.

## Screen Layout

```
┌─────────────────────────────────────────────────────────────┐
│ ExecutiveHeader                                             │
├──────────┬──────────────────────────────────────────────────┤
│          │ Breadcrumb: Knowledge > Knowledge Base            │
│ Workspace├──────────────────────────────────────────────────┤
│   Nav    │ KnowledgeBaseHeader (search, filters)            │
│          ├──────────────────────────────────────────────────┤
│          │ KnowledgeBase (main content)                     │
│          │ ┌────────────────────────────────────────────┐   │
│          │ │ Tabs: [Documents] [Entries] [Tags] [Search]│   │
│          │ ├────────────────────────────────────────────┤   │
│          │ │ DocumentLibrary (file cards)                │   │
│          │ │ KnowledgeEntries (article cards)            │   │
│          │ │ TagCloud (tag visualization)                │   │
│          │ │ SearchResults (search + filters)            │   │
│          │ └────────────────────────────────────────────┘   │
├──────────┴──────────────────────────────────────────────────┤
│ AiDock (knowledge suggestions, related content)             │
└─────────────────────────────────────────────────────────────┘
```

## Component Tree

```
KnowledgeBasePage
├── ExecutiveHeader
├── Breadcrumb
├── KnowledgeBaseHeader
│   ├── SearchBar (full-text search)
│   ├── ChipSelect (tags)
│   ├── ChipSelect (categories)
│   └── Button (Create Entry)
├── KnowledgeBase
│   ├── Tabs
│   │   ├── DocumentsTab
│   │   │   └── DocumentGrid
│   │   │       └── DocumentCard × N
│   │   │           ├── thumbnail
│   │   │           ├── title
│   │   │           ├── tags
│   │   │           └── updated_at
│   │   ├── EntriesTab
│   │   │   └── EntryList
│   │   │       └── EntryCard × N
│   │   │           ├── title
│   │   │           ├── excerpt
│   │   │           ├── author
│   │   │           └── ConfidenceBadge
│   │   ├── TagsTab
│   │   │   └── TagCloud
│   │   │       └── Tag × N
│   │   │           ├── name
│   │   │           └── count
│   │   └── SearchTab
│   │       └── SearchResults
│   │           ├── filters
│   │           └── result_list
│   └── EntryEditor
│       ├── Input (title)
│       ├── Textarea (content)
│       ├── ChipSelect (tags)
│       └── Button (Save)
└── AiDock
    ├── AgentCard (Knowledge Agent)
    └── EvidencePanel (related content)
```

## Data Sources

### Knowledge Entries
```typescript
// API: GET /api/v1/knowledge/entries
interface KnowledgeEntryList {
  entries: KnowledgeEntry[];
  total_count: number;
}

interface KnowledgeEntry {
  entry_id: string;
  title: string;
  content: string;
  excerpt: string;
  tags: string[];
  category: string;
  author: string;
  created_at: string;
  updated_at: string;
  confidence: number;
  source?: string;
}
```

### Documents
```typescript
// API: GET /api/v1/knowledge/documents
interface KnowledgeDocumentList {
  documents: KnowledgeDocument[];
  total_count: number;
}

interface KnowledgeDocument {
  document_id: string;
  title: string;
  type: string;
  size: number;
  thumbnail_url?: string;
  tags: string[];
  uploaded_by: string;
  uploaded_at: string;
  download_count: number;
}
```

### React Query
```typescript
const { data: entries } = useQuery({
  queryKey: ['knowledge', 'entries', filters],
  queryFn: () => api.get('/api/v1/knowledge/entries', { params: filters }),
});

const { data: documents } = useQuery({
  queryKey: ['knowledge', 'documents', filters],
  queryFn: () => api.get('/api/v1/knowledge/documents', { params: filters }),
});

const createEntry = useMutation({
  mutationFn: (request: CreateEntryRequest) => api.post('/api/v1/knowledge/entries', request),
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ['knowledge', 'entries'] });
    toast.success('Entry created');
  },
});
```

## Zustand Store
```typescript
// stores/knowledgeBaseStore.ts
interface KnowledgeBaseState {
  activeTab: 'documents' | 'entries' | 'tags' | 'search';
  searchQuery: string;
  selectedTags: string[];
  selectedCategories: string[];
  setTab: (tab: string) => void;
  setSearch: (query: string) => void;
  setTags: (tags: string[]) => void;
  setCategories: (categories: string[]) => void;
}
```

## Interactions

### Search
1. Type in search bar
2. Debounce 300ms
3. Update results
4. Highlight matches

### Document View
1. Click document card
2. Open DocumentViewer
3. View content
4. Download or share

### Entry Editor
1. Click "Create Entry"
2. Open EntryEditor
3. Write content
4. Add tags
5. Save entry

### Tag Navigation
1. Click tag in cloud
2. Filter by tag
3. Show related content
4. Update URL params

## Responsive Breakpoints

| Breakpoint | Layout |
|------------|--------|
| Desktop (>1024px) | Grid view for documents |
| Tablet (768-1024px) | List view |
| Mobile (<768px) | Single column, swipe |

## Loading States
- Documents: Skeleton grid
- Entries: Skeleton cards
- Tags: Skeleton cloud

## Error States
- No results: EmptyState
- API error: Toast notification
- Save failure: Draft recovery

## Accessibility
- Cards are focusable
- Search results announced via `aria-live`
- Screen reader: "Entry X, confidence Y%"
- Keyboard: Enter to open, Tab to navigate

## Telemetry
- `knowledge_base.view` — Screen loaded
- `knowledge_base.search` — Search performed
- `knowledge_base.entry_create` — Entry created
- `knowledge_base.document_view` — Document viewed

## Implementation Notes
- 4 tabs with different views
- Full-text search with filters
- EntryEditor for content creation
- AiDock provides knowledge suggestions
- TagCloud for visual navigation
