# KNOW-002: Document Tools Screen Specification

**Module:** `features/knowledge/DocumentToolsPage`
**Layer:** features
**Version:** 1.0.0
**Status:** Draft
**Workspace:** Knowledge

## Purpose
Document management, template library, batch processing, and document AI tools for tender documentation.

## Screen Layout

```
┌─────────────────────────────────────────────────────────────┐
│ ExecutiveHeader                                             │
├──────────┬──────────────────────────────────────────────────┤
│          │ Breadcrumb: Knowledge > Document Tools            │
│ Workspace├──────────────────────────────────────────────────┤
│   Nav    │ DocumentToolsHeader (search, upload)             │
│          ├──────────────────────────────────────────────────┤
│          │ DocumentTools (main content)                     │
│          │ ┌────────────────────────────────────────────┐   │
│          │ │ Tabs: [Library] [Templates] [Batch] [AI]   │   │
│          │ ├────────────────────────────────────────────┤   │
│          │ │ DocumentLibrary (file explorer)             │   │
│          │ │ TemplateLibrary (template cards)            │   │
│          │ │ BatchProcessor (upload + process)          │   │
│          │ │ DocumentAI (extraction tools)              │   │
│          │ └────────────────────────────────────────────┘   │
├──────────┴──────────────────────────────────────────────────┤
│ AiDock (document analysis, template suggestions)            │
└─────────────────────────────────────────────────────────────┘
```

## Component Tree

```
DocumentToolsPage
├── ExecutiveHeader
├── Breadcrumb
├── DocumentToolsHeader
│   ├── SearchBar (document search)
│   ├── FileUpload (drag & drop)
│   └── Button (Create Template)
├── DocumentTools
│   ├── Tabs
│   │   ├── LibraryTab
│   │   │   └── FileExplorer
│   │   │       ├── FolderTree
│   │   │       └── FileList
│   │   │           └── DocumentCard × N
│   │   ├── TemplatesTab
│   │   │   └── TemplateLibrary
│   │   │       └── TemplateCard × N
│   │   ├── BatchTab
│   │   │   └── BatchProcessor
│   │   │       ├── FileUpload
│   │   │       ├── ProcessingQueue
│   │   │       └── ResultsTable
│   │   └── AITab
│   │       └── DocumentAI
│   │           ├── TDSExtractor
│   │           ├── BOQParser
│   │           └── ComplianceChecker
│   └── DocumentPreview
│       └── DocumentViewer
└── AiDock
    ├── AgentCard (Document Agent)
    └── EvidencePanel (extraction results)
```

## Data Sources

### Document Library
```typescript
// API: GET /api/v1/files/list
interface DocumentList {
  folders: Folder[];
  files: FileItem[];
  total_count: number;
  total_size: number;
}

interface Folder {
  folder_id: string;
  name: string;
  path: string;
  file_count: number;
  created_at: string;
}

interface FileItem {
  file_id: string;
  name: string;
  type: string;
  size: number;
  path: string;
  uploaded_at: string;
  uploaded_by: string;
  tags: string[];
}
```

### Templates
```typescript
// API: GET /api/v1/files/templates
interface TemplateList {
  templates: Template[];
}

interface Template {
  template_id: string;
  name: string;
  description: string;
  category: string;
  file_url: string;
  preview_url: string;
  usage_count: number;
  created_at: string;
}
```

### Batch Processing
```typescript
// API: POST /api/v1/files/batch-process
interface BatchProcessRequest {
  file_ids: string[];
  process_type: 'tds_extraction' | 'boq_parse' | 'compliance_check';
  options?: Record<string, any>;
}

interface BatchProcessResponse {
  batch_id: string;
  status: 'queued' | 'processing' | 'completed' | 'failed';
  progress: number;
  results?: ProcessResult[];
}

interface ProcessResult {
  file_id: string;
  status: 'success' | 'failed';
  output?: any;
  error?: string;
}
```

### React Query
```typescript
const { data: documents } = useQuery({
  queryKey: ['files', 'list', currentFolder],
  queryFn: () => api.get('/api/v1/files/list', { params: { folder: currentFolder } }),
});

const { data: templates } = useQuery({
  queryKey: ['files', 'templates'],
  queryFn: () => api.get('/api/v1/files/templates'),
});

const uploadFile = useMutation({
  mutationFn: (formData: FormData) => api.post('/api/v1/files/upload', formData),
});

const batchProcess = useMutation({
  mutationFn: (request: BatchProcessRequest) => api.post('/api/v1/files/batch-process', request),
});
```

## Zustand Store
```typescript
// stores/documentToolsStore.ts
interface DocumentToolsState {
  activeTab: 'library' | 'templates' | 'batch' | 'ai';
  currentFolder: string | null;
  selectedFiles: Set<string>;
  previewFile: string | null;
  setTab: (tab: string) => void;
  setFolder: (folder: string | null) => void;
  toggleFile: (fileId: string) => void;
  setPreview: (fileId: string | null) => void;
}
```

## Interactions

### File Upload
1. Drag files to upload zone
2. Or click to browse
3. Show upload progress
4. Refresh file list on complete

### Template Usage
1. Click template card
2. Preview template
3. Use template → create document
4. Track usage count

### Batch Processing
1. Select files
2. Choose process type
3. Start batch
4. Monitor progress
5. View results

### Document Preview
1. Click file in library
2. Open DocumentViewer
3. View content
4. Download or share

## Responsive Breakpoints

| Breakpoint | Layout |
|------------|--------|
| Desktop (>1024px) | 2-column (explorer + preview) |
| Tablet (768-1024px) | Tabbed view |
| Mobile (<768px) | Full-screen list, swipe preview |

## Loading States
- File list: Skeleton rows
- Templates: Skeleton cards
- Upload: Progress bar
- Batch: Progress indicator

## Error States
- Upload failure: Retry button
- Processing failure: Error details
- Network error: Toast notification

## Accessibility
- Files are focusable
- Upload zone keyboard accessible
- Screen reader: "File X, size Y"
- Keyboard: Enter to open, Delete to remove

## Telemetry
- `document_tools.view` — Screen loaded
- `document_tools.upload` — File uploaded
- `document_tools.template_use` — Template used
- `document_tools.batch_process` — Batch started

## Implementation Notes
- FileExplorer for document management
- Drag-and-drop upload
- Batch processing with progress
- AiDock provides document analysis
- DocumentViewer for preview
