# KNOW-020: Document Management Screen Specification

**Module:** `features/document-management/DocumentManagementPage`
**Layer:** features
**Version:** 1.0.0
**Status:** Draft
**Workspace:** Knowledge

## Purpose
Manage, organize, and search knowledge base documents.

## Screen Layout

```
┌─────────────────────────────────────────────────────────────┐
│ ExecutiveHeader                                             │
├──────────┬──────────────────────────────────────────────────┤
│          │ Breadcrumb: Knowledge > Document Management       │
│ Workspace├──────────────────────────────────────────────────┤
│   Nav    │ DocumentManagementHeader (count, categories)     │
│          ├──────────────────────────────────────────────────┤
│          │ DocumentManagement (main content)                │
│          │ ┌────────────────────────────────────────────┐   │
│          │ │ SearchBar (document search)                 │   │
│          │ ├────────────────────────────────────────────┤   │
│          │ │ DocumentGrid (document cards)               │   │
│          │ │ ┌──────┬──────┬──────┬──────┐              │   │
│          │ │ │Doc 1 │Doc 2 │Doc 3 │Doc 4 │              │   │
│          │ │ │      │      │      │      │              │   │
│          │ │ └──────┴──────┴──────┴──────┘              │   │
│          │ ├────────────────────────────────────────────┤   │
│          │ │ DocumentDetails (selected document)         │   │
│          │ └────────────────────────────────────────────┘   │
├──────────┴──────────────────────────────────────────────────┤
│ AiDock (document suggestions)                               │
└─────────────────────────────────────────────────────────────┘
```

## Component Tree

```
DocumentManagementPage
├── ExecutiveHeader
├── Breadcrumb
├── DocumentManagementHeader
│   ├── KpiStrip (document_count, category_count)
│   └── Button (Upload Document)
├── DocumentManagement
│   ├── SearchBar
│   │   └── SearchInput
│   ├── FilterPanel
│   │   ├── ChipSelect (category)
│   │   ├── ChipSelect (type)
│   │   └── ChipSelect (date_range)
│   ├── DocumentGrid
│   │   └── DocumentCard × N
│   │       ├── icon
│   │       ├── title
│   │       ├── excerpt
│   │       ├── category
│   │       ├── updated_at
│   │       └── Button (View)
│   ├── DocumentDetails
│   │   ├── document_info
│   │   ├── content_preview
│   │   ├── metadata
│   │   └── related_documents
│   ├── CategoryTree
│   │   └── Category × N
│   │       ├── name
│   │       ├── count
│   │       └── children
│   └── DocumentStats
│       ├── chart (documents_by_category)
│       └── chart (documents_by_type)
└── AiDock
    ├── AgentCard (Document Agent)
    └── EvidencePanel (document suggestions)
```

## Data Sources

### Documents
```typescript
// API: GET /api/v1/knowledge/documents
interface DocumentList {
  documents: Document[];
  total_count: number;
  categories: Category[];
}

interface Document {
  document_id: string;
  title: string;
  content: string;
  excerpt: string;
  category: string;
  type: string;
  tags: string[];
  created_at: string;
  updated_at: string;
  author: string;
}

interface Category {
  category_id: string;
  name: string;
  count: number;
  children: Category[];
}
```

### React Query
```typescript
const { data: documents } = useQuery({
  queryKey: ['knowledge', 'documents', filters],
  queryFn: () => api.get('/api/v1/knowledge/documents', { params: filters }),
});

const uploadDocument = useMutation({
  mutationFn: (document: UploadDocumentRequest) => api.post('/api/v1/knowledge/documents', document),
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ['knowledge', 'documents'] });
    toast.success('Document uploaded');
  },
});

const deleteDocument = useMutation({
  mutationFn: (documentId: string) => api.delete(`/api/v1/knowledge/documents/${documentId}`),
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ['knowledge', 'documents'] });
    toast.success('Document deleted');
  },
});
```

## Zustand Store
```typescript
// stores/documentManagementStore.ts
interface DocumentManagementState {
  searchQuery: string;
  filters: {
    category: string[];
    type: string[];
    date_range: { start: string; end: string } | null;
  };
  setSearch: (query: string) => void;
  setFilter: <K extends keyof DocumentManagementState['filters']>(key: K, value: DocumentManagementState['filters'][K]) => void;
}
```

## Interactions

### Search Documents
1. Type query
2. Search documents
3. View results
4. Select document

### Upload Document
1. Click Upload
2. Select file
3. Add metadata
4. Save document

### View Document
1. Click document card
2. View details
3. Read content
4. Check metadata

### Manage Categories
1. View category tree
2. Expand/collapse
3. Filter by category
4. Create new category

## Responsive Breakpoints

| Breakpoint | Layout |
|------------|--------|
| Desktop (>1024px) | Full grid + details |
| Tablet (768-1024px) | Grid with modal details |
| Mobile (<768px) | Simplified list |

## Loading States
- Documents: Skeleton cards
- Details: Loading spinner
- Upload: Progress indicator

## Error States
- Upload failure: Toast error
- Delete failure: Toast error
- Network error: Toast notification

## Accessibility
- Documents are focusable
- Count announced via `aria-live`
- Screen reader: "Document: BOQ Guide, category: Technical"
- Keyboard: Tab through documents

## Telemetry
- `document_management.view` — Screen loaded
- `document_management.search` — Search performed
- `document_management.upload` — Document uploaded
- `document_management.delete` — Document deleted

## Implementation Notes
- Document management
- Category organization
- Search functionality
- AiDock provides document suggestions
- Version control
