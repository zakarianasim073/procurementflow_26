# KNOW-011: Document Viewer Screen Specification

**Module:** `features/document-viewer/DocumentViewerPage`
**Layer:** features
**Version:** 1.0.0
**Status:** Draft
**Workspace:** Knowledge

## Purpose
Universal document viewer with annotations, collaboration, and export.

## Screen Layout

```
┌─────────────────────────────────────────────────────────────┐
│ ExecutiveHeader                                             │
├──────────┬──────────────────────────────────────────────────┤
│          │ Breadcrumb: Knowledge > Document Viewer           │
│ Workspace├──────────────────────────────────────────────────┤
│   Nav    │ DocumentViewerHeader (document info, actions)    │
│          ├──────────────────────────────────────────────────┤
│          │ DocumentViewer (main content)                    │
│          │ ┌────────────────────────────────────────────┐   │
│          │ │ Toolbar (zoom, navigate, annotate)          │   │
│          │ ├────────────────────────────────────────────┤   │
│          │ │ DocumentCanvas (rendered document)          │   │
│          │ │ ┌──────────────────────────────────────────┐│   │
│          │ │ │ PDF/DOCX/Image content                   ││   │
│          │ │ │ with annotations highlighted             ││   │
│          │ │ └──────────────────────────────────────────┘│   │
│          │ ├────────────────────────────────────────────┤   │
│          │ │ Sidebar (annotations, metadata)             │   │
│          │ └────────────────────────────────────────────┘   │
├──────────┴──────────────────────────────────────────────────┤
│ AiDock (document insights, extraction)                      │
└─────────────────────────────────────────────────────────────┘
```

## Component Tree

```
DocumentViewerPage
├── ExecutiveHeader
├── Breadcrumb
├── DocumentViewerHeader
│   ├── document_info
│   ├── ButtonGroup (Download, Share, Print)
│   └── Button (Analyze)
├── DocumentViewer
│   ├── Toolbar
│   │   ├── ButtonGroup (zoom in/out, fit)
│   │   ├── ButtonGroup (prev/next page)
│   │   ├── Button (Annotate)
│   │   └── Button (Full Screen)
│   ├── DocumentCanvas
│   │   ├── PDFViewer
│   │   ├── DocxViewer
│   │   └── ImageViewer
│   └── Sidebar
│       ├── Tabs: [Annotations] [Metadata] [Outline]
│       ├── AnnotationList
│       │   └── Annotation × N
│       │       ├── text
│       │       ├── author
│       │       └── timestamp
│       ├── MetadataPanel
│       │   └── metadata_fields
│       └── OutlinePanel
│           └── outline_items
└── AiDock
    ├── AgentCard (Document Agent)
    └── EvidencePanel (document insights)
```

## Data Sources

### Document
```typescript
// API: GET /api/v1/files/{file_id}
interface Document {
  file_id: string;
  name: string;
  type: string;
  size: number;
  url: string;
  metadata: Record<string, any>;
  created_at: string;
  updated_at: string;
}
```

### Annotations
```typescript
// API: GET /api/v1/files/{file_id}/annotations
interface AnnotationList {
  annotations: Annotation[];
}

interface Annotation {
  annotation_id: string;
  page: number;
  x: number;
  y: number;
  width: number;
  height: number;
  text: string;
  author: string;
  created_at: string;
  color: string;
}
```

### React Query
```typescript
const { data: document } = useQuery({
  queryKey: ['files', fileId],
  queryFn: () => api.get(`/api/v1/files/${fileId}`),
});

const { data: annotations } = useQuery({
  queryKey: ['files', fileId, 'annotations'],
  queryFn: () => api.get(`/api/v1/files/${fileId}/annotations`),
});

const addAnnotation = useMutation({
  mutationFn: (request: AddAnnotationRequest) =>
    api.post(`/api/v1/files/${fileId}/annotations`, request),
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ['files', fileId, 'annotations'] });
    toast.success('Annotation added');
  },
});
```

## Zustand Store
```typescript
// stores/documentViewerStore.ts
interface DocumentViewerState {
  zoom: number;
  currentPage: number;
  showAnnotations: boolean;
  setZoom: (zoom: number) => void;
  setPage: (page: number) => void;
  setShowAnnotations: (show: boolean) => void;
}
```

## Interactions

### Zoom Document
1. Click zoom buttons
2. Adjust zoom level
3. Update canvas
4. Preserve position

### Navigate Pages
1. Click prev/next buttons
2. Update page
3. Scroll to top
4. Update page indicator

### Add Annotation
1. Click Annotate button
2. Select area
3. Enter text
4. Save annotation

### View Metadata
1. Click Metadata tab
2. View document info
3. Copy metadata
4. Export if needed

## Responsive Breakpoints

| Breakpoint | Layout |
|------------|--------|
| Desktop (>1024px) | Full viewer + sidebar |
| Tablet (768-1024px) | Viewer + collapsible sidebar |
| Mobile (<768px) | Full-screen viewer, bottom sheet |

## Loading States
- Document: Loading spinner
- Annotations: Skeleton list
- Canvas: Loading indicator

## Error States
- Load failure: Retry button
- Unsupported format: Download instead
- Network error: Toast notification

## Accessibility
- Document is scrollable
- Annotations are focusable
- Screen reader: "Page X of Y"
- Keyboard: Arrow keys to navigate, +/- to zoom

## Telemetry
- `document_viewer.view` — Screen loaded
- `document_viewer.zoom` — Zoom changed
- `document_viewer.navigate` — Page navigated
- `document_viewer.annotate` — Annotation added

## Implementation Notes
- Multi-format support (PDF, DOCX, Image)
- Annotation system
- Zoom and navigation
- AiDock provides document insights
- Export and share functionality
