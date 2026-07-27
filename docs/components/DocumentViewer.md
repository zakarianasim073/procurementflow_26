# DocumentViewer Component Contract

**Package**: `widgets/ai`  
**Type**: Document Display Component  
**Stability**: Stable  

---

## Purpose

Displays tender documents (PDF, DOCX, images) with annotation, search, and extraction capabilities. Core to TEN-001 BOQ & Documents, TEN-003 Compliance, and TEN-005 Award screens.

---

## Props

```typescript
interface DocumentViewerProps {
  /** Document source */
  src: string; // URL or blob URL
  /** Document type */
  type: 'pdf' | 'docx' | 'image' | 'txt';
  /** Document metadata */
  metadata?: {
    title: string;
    pages?: number;
    size: number;
    lastModified: string;
    extractedText?: string;
    annotations?: Annotation[];
  };
  /** Viewer configuration */
  config?: {
    /** Enable text selection */
    enableTextSelection?: boolean;
    /** Enable annotations */
    enableAnnotations?: boolean;
    /** Enable search */
    enableSearch?: boolean;
    /** Enable thumbnail sidebar */
    showThumbnails?: boolean;
    /** Enable outline/bookmarks */
    showOutline?: boolean;
    /** Default zoom level */
    defaultZoom?: number; // 0.5-3.0
    /** Page mode */
    pageMode?: 'single' | 'continuous' | 'facing';
  };
  /** Event handlers */
  onPageChange?: (page: number, totalPages: number) => void;
  onAnnotationAdd?: (annotation: Annotation) => void;
  onAnnotationUpdate?: (annotation: Annotation) => void;
  onAnnotationDelete?: (annotationId: string) => void;
  onSearchResults?: (results: SearchResult[]) => void;
  onError?: (error: Error) => void;
  /** Loading state */
  loading?: boolean;
  /** Custom className */
  className?: string;
}

interface Annotation {
  id: string;
  page: number;
  type: 'highlight' | 'note' | 'redaction' | 'stamp' | 'signature';
  position: { x: number; y: number; width: number; height: number };
  content: string;
  author: string;
  color: string;
  createdAt: string;
  updatedAt: string;
}

interface SearchResult {
  page: number;
  matches: { text: string; position: number; length: number }[];
  context: string;
}
```

---

## Slots

| Slot | Required | Description |
|------|----------|-------------|
| `toolbar` | No | Custom toolbar buttons |
| `sidebar` | No | Custom sidebar content (thumbnails, outline, search) |
| `annotationTools` | No | Custom annotation toolbar |
| `footer` | No | Page info, zoom controls |

---

## State

| State | Trigger | Visual |
|-------|---------|--------|
| `loading` | `loading=true` or initial load | Skeleton with page placeholders |
| `ready` | Document loaded | Full viewer with toolbar |
| `error` | Load failed | Error message + retry |
| `searching` | Search in progress | Spinner in search input |
| `annotating` | Annotation tool active | Crosshair cursor, tool palette |

---

## Accessibility

- **Role**: `application` (PDF.js) or `img` (images)
- **Keyboard**: Full keyboard navigation (arrows, +/- zoom, Home/End)
- **Screen Reader**: Page announced on change, search results announced
- **Zoom**: `aria-label` on zoom controls
- **Search**: `aria-live="polite"` for results
- **Annotations**: `aria-label` per annotation

---

## Loading

- **Progressive**: First page renders immediately, rest lazy
- **Skeleton**: Page placeholders with shimmer
- **Delay**: Show skeleton after 200ms

---

## Errors

- **Network**: "Failed to load document — check connection"
- **Corrupt**: "Document appears corrupted — try re-downloading"
- **Unsupported**: "File type not supported"
- **Password**: "Document is password protected"

---

## Keyboard

| Key | Action |
|-----|--------|
| `Arrow Left/Right` | Previous/next page |
| `Arrow Up/Down` | Scroll within page |
| `+/-` | Zoom in/out |
| `0` | Fit to width |
| `Home` / `End` | First/last page |
| `Ctrl+F` | Focus search |
| `Escape` | Clear search / close sidebar |
| `A` | Add annotation (when enabled) |

---

## Mobile

- **< 768px**: 
  - Single page mode forced
  - Toolbar collapsed to bottom bar
  - Sidebar as bottom sheet
  - Touch pinch-to-zoom
  - Swipe for page navigation
- **Toolbar**: Bottom fixed with page indicator

---

## Permissions

| Role | View | Annotate | Download | Print |
|------|------|----------|----------|-------|
| `viewer` | ✅ | ❌ | ❌ | ❌ |
| `estimator` | ✅ | ✅ | ✅ | ✅ |
| `compliance` | ✅ | ✅ | ✅ | ✅ |
| `admin` | ✅ | ✅ | ✅ | ✅ |

---

## Telemetry

| Event | Properties |
|-------|------------|
| `document_view` | `doc_type`, `pages`, `duration_ms` |
| `document_search` | `query`, `results_count`, `page` |
| `document_annotate` | `type`, `page`, `tool` |
| `document_download` | `doc_type`, `page_range` |
| `document_print` | `pages`, `format` |

---

## React Query

```typescript
// Document metadata from tender API
const { data } = useQuery({
  queryKey: tenderKeys.document(tenderId, docType),
  select: (response) => ({
    src: response.download_url,
    metadata: { ...response, extractedText: response.text }
  })
});
```

---

## Dependencies

- `pdfjs-dist` (PDF rendering)
- `mammoth` (DOCX rendering)
- `pdfjs-dist/web/pdf_viewer.css` (PDF.js viewer styles)
- `Toolbar` (navigation, zoom, search)
- `Sidebar` (thumbnails, outline, search results)
- `AnnotationLayer` (annotations overlay)
- `AnnotationTools` (highlight, note, stamp, signature)
- `SearchHighlighter` (search result highlighting)
- `ZoomControl` (zoom in/out/fit)
- `PageNavigation` (page input, prev/next)
- `lucide-react`: `Search`, `ZoomIn`, `ZoomOut`, `RotateCw`, `Download`, `Print`, `FileText`, `Highlighter`, `Stamp`, `PenTool`, `Signature`, `Sidebar`, `ChevronLeft`, `ChevronRight`

---

## PDF.js Configuration

```typescript
// Worker setup (in app initialization)
pdfjsLib.GlobalWorkerOptions.workerSrc = '/pdf.worker.min.js';

// Viewer options
const viewerOptions = {
  enableTextSelection: true,
  enableAnnotation: true,
  renderInteractiveForms: true,
  useOnlyCssZoom: false,
  maxCanvasPixels: 16777216
};
```

---

## Future Extensions

- [ ] Collaborative annotations (real-time)
- [ ] AI-powered clause extraction highlight
- [ ] Version comparison (side-by-side)
- [ ] OCR for scanned PDFs
- [ ] Digital signature workflow
- [ ] Redaction with audit trail
- [ ] Batch document viewing