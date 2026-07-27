# TEN-010: Document Manager Screen Specification

**Module:** `features/document-manager/DocumentManagerPage`
**Layer:** features
**Version:** 1.0.0
**Status:** Draft
**Workspace:** Acquisition

## Purpose
Tender document management, organization, and version control.

## Screen Layout

```
┌─────────────────────────────────────────────────────────────┐
│ ExecutiveHeader                                             │
├──────────┬──────────────────────────────────────────────────┤
│          │ Breadcrumb: Acquisition > Document Manager        │
│ Workspace├──────────────────────────────────────────────────┤
│   Nav    │ DocumentManagerHeader (tender context)           │
│          ├──────────────────────────────────────────────────┤
│          │ DocumentManager (main content)                   │
│          │ ┌────────────────────────────────────────────┐   │
│          │ │ FileExplorer (folder tree + file list)      │   │
│          │ │ ┌──────────────┬──────────────────────┐     │   │
│          │ │ │ FolderTree   │ FileList              │     │   │
│          │ │ │ ├── Documents│ ├── notice.pdf        │     │   │
│          │ │ │ ├── BOQ      │ ├── boq.pdf           │     │   │
│          │ │ │ ├── TDS      │ ├── tds.pdf           │     │   │
│          │ │ │ └── Forms    │ └── forms.docx        │     │   │
│          │ │ └──────────────┴──────────────────────┘     │   │
│          │ ├────────────────────────────────────────────┤   │
│          │ │ DocumentViewer (preview)                    │   │
│          │ └────────────────────────────────────────────┘   │
├──────────┴──────────────────────────────────────────────────┤
│ AiDock (document analysis, extraction)                      │
└─────────────────────────────────────────────────────────────┘
```

## Component Tree

```
DocumentManagerPage
├── ExecutiveHeader
├── Breadcrumb
├── DocumentManagerHeader
│   ├── TenderCard (compact)
│   └── ButtonGroup (Upload, Download All, Analyze)
├── DocumentManager
│   ├── SplitPane (horizontal)
│   │   ├── FileExplorer
│   │   │   ├── FolderTree
│   │   │   │   └── Folder × N
│   │   │   │       ├── name
│   │   │   │       ├── file_count
│   │   │   │       └── children (recursive)
│   │   │   └── FileList
│   │   │       └── DocumentCard × N
│   │   │           ├── icon
│   │   │           ├── name
│   │   │           ├── size
│   │   │           ├── modified_at
│   │   │           └── actions (view, download, delete)
│   │   └── DocumentViewer
│   │       ├── PDFViewer
│   │       ├── DocxViewer
│   │       └── ImageViewer
│   └── DocumentInfo
│       ├── metadata
│       ├── version_history
│       └── tags
└── AiDock
    ├── AgentCard (Document Agent)
    └── EvidencePanel (document analysis)
```

## Data Sources

### Document Tree
```typescript
// API: GET /api/v1/files/tree/{tender_id}
interface DocumentTree {
  folders: Folder[];
  files: FileItem[];
}

interface Folder {
  folder_id: string;
  name: string;
  path: string;
  file_count: number;
  children: Folder[];
}

interface FileItem {
  file_id: string;
  name: string;
  type: string;
  size: number;
  path: string;
  uploaded_at: string;
  version: number;
}
```

### Document Versions
```typescript
// API: GET /api/v1/files/{file_id}/versions
interface VersionList {
  versions: Version[];
}

interface Version {
  version_id: string;
  version_number: number;
  uploaded_at: string;
  uploaded_by: string;
  size: number;
  change_notes?: string;
}
```

### React Query
```typescript
const { data: tree } = useQuery({
  queryKey: ['files', 'tree', tenderId],
  queryFn: () => api.get(`/api/v1/files/tree/${tenderId}`),
});

const { data: versions } = useQuery({
  queryKey: ['files', fileId, 'versions'],
  queryFn: () => api.get(`/api/v1/files/${fileId}/versions`),
  enabled: !!fileId,
});

const uploadFile = useMutation({
  mutationFn: (formData: FormData) => api.post('/api/v1/files/upload', formData),
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ['files', 'tree', tenderId] });
    toast.success('File uploaded');
  },
});
```

## Zustand Store
```typescript
// stores/documentManagerStore.ts
interface DocumentManagerState {
  selectedFolder: string | null;
  selectedFile: string | null;
  viewMode: 'list' | 'grid';
  setFolder: (id: string | null) => void;
  setFile: (id: string | null) => void;
  setViewMode: (mode: string) => void;
}
```

## Interactions

### Navigate Folders
1. Click folder in tree
2. Expand/collapse
3. Update file list
4. Show folder contents

### View Document
1. Click file in list
2. Open DocumentViewer
3. Preview content
4. Show metadata

### Upload Document
1. Click Upload button
2. Select files
3. Choose folder
4. Upload with progress

### Download Document
1. Click Download button
2. Choose version
3. Download file
4. Show progress

## Responsive Breakpoints

| Breakpoint | Layout |
|------------|--------|
| Desktop (>1024px) | Split pane (tree + viewer) |
| Tablet (768-1024px) | Stacked (tree + viewer) |
| Mobile (<768px) | Full-screen list, swipe viewer |

## Loading States
- Tree: Skeleton folders
- Files: Skeleton cards
- Viewer: Loading spinner

## Error States
- Upload failure: Retry button
- Preview failure: Download instead
- Network error: Toast notification

## Accessibility
- Tree items are focusable
- File selection announced via `aria-live`
- Screen reader: "Folder X, Y files"
- Keyboard: Arrow keys to navigate, Enter to open

## Telemetry
- `document_manager.view` — Screen loaded
- `document_manager.folder_click` — Folder selected
- `document_manager.file_view` — File viewed
- `document_manager.upload` — File uploaded
- `document_manager.download` — File downloaded

## Implementation Notes
- FileExplorer for document navigation
- DocumentViewer for preview
- Version history for tracking
- AiDock provides document analysis
- Drag-and-drop upload
