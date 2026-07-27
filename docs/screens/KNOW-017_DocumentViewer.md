# KNOW-017: Document Viewer Screen Specification

**Module:** `features/document-viewer/DocumentViewerPage`
**Layer:** features
**Version:** 1.0.0
**Status:** Draft
**Workspace:** Knowledge

## Purpose
View, annotate, and analyze tender documents and PDFs.

## Screen Layout

```
┌─────────────────────────────────────────────────────────────┐
│ ExecutiveHeader                                             │
├──────────┬──────────────────────────────────────────────────┤
│          │ Breadcrumb: Knowledge > Document Viewer           │
│ Workspace├──────────────────────────────────────────────────┤
│   Nav    │ DocumentViewerHeader (document, version)         │
│          ├──────────────────────────────────────────────────┤
│          │ DocumentViewer (main content)                    │
│          │ ┌────────────────────────────────────────────┐   │
│          │ │ Toolbar (view controls)                     │   │
│          │ ├────────────────────────────────────────────┤   │
│          │ │ DocumentCanvas (PDF/document view)          │   │
│          │ │ ┌──────────────────────────────────────────┐│   │
│          │ │ │                                          ││   │
│          │ │ │         [Document Content]                ││   │
│          │ │ │                                          ││   │
│          │ │ └──────────────────────────────────────────┘│   │
│          │ ├────────────────────────────────────────────┤   │
│          │ │ AnnotationPanel (annotations)               │   │
│          │ └────────────────────────────────────────────┘   │
├──────────┴──────────────────────────────────────────────────┤
│ AiDock (document insights, AI analysis)                     │
└─────────────────────────────────────────────────────────────┘
```

## Component Tree

```
DocumentViewerPage
├── ExecutiveHeader
├── Breadcrumb
├── DocumentViewerHeader
│   ├── document_info
│   ├── version_selector
│   └── actions (download, share, annotate)
├── DocumentViewer
│   ├── Toolbar
│   │   ├── zoom_controls
│   │   ├── page_navigation
│   │   ├── view_mode
│   │   └── annotation_tools
│   ├── DocumentCanvas
│   │   ├── PDFViewer
│   │   ├── ImageViewer
│   │   └── TextViewer
│   ├── AnnotationPanel
│   │   └── Annotation × N
│   │       ├── text
│   │       ├── author
│   │       ├── timestamp
│   │       └── actions (edit, delete)
│   └── DocumentOutline
│       ├── chapters
│       └── bookmarks
└── AiDock
    ├── AgentCard (Document Agent)
    └── EvidencePanel (document insights)
```

## Data Sources

### Document
```typescript
// API: GET /api/v1/documents/{document_id}
interface Document {
  document_id: string;
  name: string;
  type: 'pdf' | 'image' | 'text';
  url: string;
  version: string;
  pages: number;
  created_at: string;
  updated_at: string;
}

interface Annotation {
  annotation_id: string;
  page: number;
  position: { x: number; y: number; width: number; height: number };
  text: string;
  author: string;
  timestamp: string;
}
```

### React Query
```typescript
const { data: document } = useQuery({
  queryKey: ['documents', documentId],
  queryFn: () => api.get(`/api/v1/documents/${documentId}`),
  enabled: !!documentId,
});

const { data: annotations } = useQuery({
  queryKey: ['documents', documentId, 'annotations'],
  queryFn: () => api.get(`/api/v1/documents/${documentId}/annotations`),
  enabled: !!documentId,
});

const addAnnotation = useMutation({
  mutationFn: (annotation: CreateAnnotationRequest) =>
    api.post(`/api/v1/documents/${documentId}/annotations`, annotation),
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ['documents', documentId, 'annotations'] });
    toast.success('Annotation added');
  },
});
```

## Zustand Store
```typescript
// stores/documentViewerStore.ts
interface DocumentViewerState {
  currentPage: number;
  zoom: number;
  viewMode: 'fit_width' | 'fit_page' | 'actual_size';
  selectedTool: string | null;
  setPage: (page: number) => void;
  setZoom: (zoom: number) => void;
  setViewMode: (mode: string) => void;
  setTool: (tool: string | null) => void;
}
```

## Interactions

### Navigate Pages
1. Click page navigation
2. Jump to page
3. Update view
4. Preserve annotations

### Zoom
1. Click zoom controls
2. Adjust zoom
3. Update view
4. Maintain position

### Add Annotation
1. Select annotation tool
2. Draw on document
3. Add text
4. Save annotation

### Download
1. Click Download
2. Choose format
3. Include annotations
4. Download file

## Responsive Breakpoints

| Breakpoint | Layout |
|------------|--------|
| Desktop (>1024px) | Full viewer + panel |
| Tablet (768-1024px) | Viewer with collapsible panel |
| Mobile (<768px) | Simplified viewer |

## Loading States
- Document: Loading PDF
- Annotations: Loading list
- Download: Progress indicator

## Error States
- Load failure: Retry button
- Unsupported format: Error message
- Network error: Toast notification

## Accessibility
- Document is keyboard navigable
- Pages announced via `aria-live`
- Screen reader: "Page 1 of 10"
- Keyboard: Arrow keys to navigate

## Telemetry
- `document_viewer.view` — Screen loaded
- `document_viewer.navigate` — Page navigated
- `document_viewer.annotate` — Annotation added
- `document_viewer.download` — Document downloaded

## Implementation Notes
- PDF rendering
- Annotation system
- Version support
- AiDock provides document insights
- Export with annotations
