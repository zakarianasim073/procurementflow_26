# TEN-026: Tender Documents Screen Specification

**Module:** `features/tender-documents/TenderDocumentsPage`
**Layer:** features
**Version:** 1.0.0
**Status:** Draft
**Workspace:** Acquisition

## Purpose
Manage and organize tender documents, uploads, and versions.

## Screen Layout

```
┌─────────────────────────────────────────────────────────────┐
│ ExecutiveHeader                                             │
├──────────┬──────────────────────────────────────────────────┤
│          │ Breadcrumb: Acquisition > Tender Documents        │
│ Workspace├──────────────────────────────────────────────────┤
│   Nav    │ TenderDocumentsHeader (count, size)              │
│          ├──────────────────────────────────────────────────┤
│          │ TenderDocuments (main content)                   │
│          │ ┌────────────────────────────────────────────┐   │
│          │ │ FileExplorer (file browser)                 │   │
│          │ │ ┌──────────────────────────────────────────┐│   │
│          │ │ │ 📁 BOQ                                    ││   │
│          │ │ │ 📁 Technical                              ││   │
│          │ │ │ 📁 Financial                              ││   │
│          │ │ │ 📄 tender_notice.pdf                     ││   │
│          │ │ └──────────────────────────────────────────┘│   │
│          │ ├────────────────────────────────────────────┤   │
│          │ │ DocumentDetails (selected file)             │   │
│          │ └────────────────────────────────────────────┘   │
├──────────┴──────────────────────────────────────────────────┤
│ AiDock (document insights)                                  │
└─────────────────────────────────────────────────────────────┘
```

## Component Tree

```
TenderDocumentsPage
├── ExecutiveHeader
├── Breadcrumb
├── TenderDocumentsHeader
│   ├── KpiStrip (file_count, total_size)
│   └── Button (Upload File)
├── TenderDocuments
│   ├── FileExplorer
│   │   ├── FolderTree
│   │   │   └── Folder × N
│   │   │       ├── name
│   │   │       ├── children
│   │   │       └── File × N
│   │   │           ├── name
│   │   │           ├── size
│   │   │           ├── modified
│   │   │           └── actions (view, download, delete)
│   │   └── Breadcrumb
│   ├── DocumentDetails
│   │   ├── file_info
│   │   ├── preview
│   │   ├── version_history
│   │   └── metadata
│   ├── UploadPanel
│   │   ├── FileUpload
│   │   ├── upload_progress
│   │   └── upload_queue
│   └── DocumentSearch
│       ├── SearchBar
│       └── SearchResults
│           └── ResultCard × N
└── AiDock
    ├── AgentCard (Document Agent)
    └── EvidencePanel (document insights)
```

## Data Sources

### Tender Documents
```typescript
// API: GET /api/v1/tenders/{tender_id}/documents
interface TenderDocuments {
  files: FileItem[];
  folders: FolderItem[];
  total_count: number;
  total_size: number;
}

interface FileItem {
  file_id: string;
  name: string;
  size: number;
  type: string;
  mime_type: string;
  created_at: string;
  updated_at: string;
  version: number;
  metadata?: Record<string, any>;
}

interface FolderItem {
  folder_id: string;
  name: string;
  children: (FileItem | FolderItem)[];
}
```

### React Query
```typescript
const { data: documents } = useQuery({
  queryKey: ['tenders', tenderId, 'documents'],
  queryFn: () => api.get(`/api/v1/tenders/${tenderId}/documents`),
  enabled: !!tenderId,
});

const uploadFile = useMutation({
  mutationFn: ({ tenderId, file, path }: { tenderId: string; file: File; path: string }) => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('path', path);
    return api.post(`/api/v1/tenders/${tenderId}/documents`, formData);
  },
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ['tenders', tenderId, 'documents'] });
    toast.success('File uploaded');
  },
});

const deleteFile = useMutation({
  mutationFn: ({ tenderId, fileId }: { tenderId: string; fileId: string }) =>
    api.delete(`/api/v1/tenders/${tenderId}/documents/${fileId}`),
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ['tenders', tenderId, 'documents'] });
    toast.success('File deleted');
  },
});
```

## Zustand Store
```typescript
// stores/tenderDocumentsStore.ts
interface TenderDocumentsState {
  currentPath: string[];
  selectedFile: string | null;
  setPath: (path: string[]) => void;
  setFile: (id: string | null) => void;
}
```

## Interactions

### Navigate Folders
1. Click folder
2. Update path
3. Load contents
4. Update explorer

### Upload File
1. Click Upload
2. Select file
3. Choose path
4. Start upload

### View File
1. Click file
2. View details
3. Preview content
4. Check versions

### Download File
1. Click Download
2. Get file URL
3. Download file
4. Save locally

## Responsive Breakpoints

| Breakpoint | Layout |
|------------|--------|
| Desktop (>1024px) | Full explorer + details |
| Tablet (768-1024px) | Explorer with modal details |
| Mobile (<768px) | Simplified list |

## Loading States
- Explorer: Loading folders
- Upload: Progress indicator
- Preview: Loading content

## Error States
- Upload failure: Toast error
- Delete failure: Toast error
- Network error: Toast notification

## Accessibility
- Files are focusable
- Path announced via `aria-live`
- Screen reader: "Folder: BOQ, 5 files"
- Keyboard: Arrow keys to navigate

## Telemetry
- `tender_documents.view` — Screen loaded
- `tender_documents.upload` — File uploaded
- `tender_documents.download` — File downloaded
- `tender_documents.delete` — File deleted

## Implementation Notes
- File explorer
- Drag-and-drop upload
- Version history
- AiDock provides document insights
- Search functionality
