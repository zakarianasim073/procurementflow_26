# KNOW-007: Document Analysis Screen Specification

**Module:** `features/document-analysis/DocumentAnalysisPage`
**Layer:** features
**Version:** 1.0.0
**Status:** Draft
**Workspace:** Knowledge

## Purpose
AI-powered document analysis, content extraction, and intelligent document processing.

## Screen Layout

```
┌─────────────────────────────────────────────────────────────┐
│ ExecutiveHeader                                             │
├──────────┬──────────────────────────────────────────────────┤
│          │ Breadcrumb: Knowledge > Document Analysis         │
│ Workspace├──────────────────────────────────────────────────┤
│   Nav    │ DocumentAnalysisHeader (upload, batch)           │
│          ├──────────────────────────────────────────────────┤
│          │ DocumentAnalysis (main content)                  │
│          │ ┌────────────────────────────────────────────┐   │
│          │ │ UploadZone (drag & drop)                    │   │
│          │ ├────────────────────────────────────────────┤   │
│          │ │ AnalysisView (document + results)           │   │
│          │ │ ┌──────────────┬──────────────────────┐     │   │
│          │ │ │ DocumentViewer│ AnalysisResults       │     │   │
│          │ │ │ (PDF/DOCX)   │ (extracted data)      │     │   │
│          │ │ └──────────────┴──────────────────────┘     │   │
│          │ └────────────────────────────────────────────┘   │
├──────────┴──────────────────────────────────────────────────┤
│ AiDock (document insights, extraction suggestions)          │
└─────────────────────────────────────────────────────────────┘
```

## Component Tree

```
DocumentAnalysisPage
├── ExecutiveHeader
├── Breadcrumb
├── DocumentAnalysisHeader
│   ├── FileUpload (drag & drop)
│   └── Button (Batch Analysis)
├── DocumentAnalysis
│   ├── UploadZone
│   │   ├── drag & drop area
│   │   └── file browser button
│   ├── AnalysisView
│   │   ├── SplitPane (horizontal)
│   │   │   ├── DocumentViewer
│   │   │   │   ├── PDFViewer
│   │   │   │   ├── highlighted sections
│   │   │   │   └── annotations
│   │   │   └── AnalysisResults
│   │   │       ├── ExtractedData
│   │   │       │   ├── key_value_pairs
│   │   │       │   ├── tables
│   │   │       │   └── entities
│   │   │       ├── ConfidenceScore
│   │   │       └── ActionButtons
│   │   │           ├── Button (Export)
│   │   │           ├── Button (Save to KB)
│   │   │           └── Button (Analyze Further)
│   │   └── AnalysisHistory
│   │       └── Table<Analysis>
│   │           ├── document_name
│   │           ├── analyzed_at
│   │           ├── confidence
│   │           └── Button (View)
│   └── BatchAnalysis
│       ├── FileList (multiple files)
│       ├── Progress (batch progress)
│       └── Results (batch results)
└── AiDock
    ├── AgentCard (Document Agent)
    └── EvidencePanel (analysis insights)
```

## Data Sources

### Document Upload
```typescript
// API: POST /api/v1/document-ai/analyze
interface AnalyzeRequest {
  file: File;
  analysis_type: 'tds' | 'boq' | 'general';
  options?: Record<string, any>;
}

interface AnalyzeResponse {
  analysis_id: string;
  status: 'processing' | 'completed' | 'failed';
  results?: AnalysisResults;
  confidence: number;
}

interface AnalysisResults {
  key_value_pairs: KeyValuePair[];
  tables: ExtractedTable[];
  entities: ExtractedEntity[];
  summary: string;
}

interface KeyValuePair {
  key: string;
  value: string;
  confidence: number;
  location?: { page: number; x: number; y: number };
}

interface ExtractedTable {
  headers: string[];
  rows: string[][];
  confidence: number;
}

interface ExtractedEntity {
  type: string;
  value: string;
  confidence: number;
}
```

### React Query
```typescript
const analyzeDocument = useMutation({
  mutationFn: (request: AnalyzeRequest) => {
    const formData = new FormData();
    formData.append('file', request.file);
    formData.append('analysis_type', request.analysis_type);
    return api.post('/api/v1/document-ai/analyze', formData);
  },
  onSuccess: (response) => {
    toast.success('Analysis completed');
    queryClient.invalidateQueries({ queryKey: ['document-ai', 'history'] });
  },
});

const { data: history } = useQuery({
  queryKey: ['document-ai', 'history'],
  queryFn: () => api.get('/api/v1/document-ai/history'),
});
```

## Zustand Store
```typescript
// stores/documentAnalysisStore.ts
interface DocumentAnalysisState {
  selectedDocument: string | null;
  analysisType: string;
  setDocument: (id: string | null) => void;
  setAnalysisType: (type: string) => void;
}
```

## Interactions

### Upload Document
1. Drag file to upload zone
2. Or click to browse
3. Select analysis type
4. Start analysis

### View Results
1. Click analysis result
2. Open DocumentViewer
3. View highlighted sections
4. Review extracted data

### Export Results
1. Click Export button
2. Choose format (JSON/CSV/Excel)
3. Include all data
4. Download file

### Save to Knowledge Base
1. Click "Save to KB"
2. Add metadata
3. Choose category
4. Save entry

## Responsive Breakpoints

| Breakpoint | Layout |
|------------|--------|
| Desktop (>1024px) | Split pane (document + results) |
| Tablet (768-1024px) | Stacked (document + results) |
| Mobile (<768px) | Full-screen viewer, swipe results |

## Loading States
- Upload: Progress bar
- Analysis: Spinner with progress
- Results: Skeleton cards

## Error States
- Upload failure: Retry button
- Analysis failure: Error details
- Network error: Toast notification

## Accessibility
- Upload zone keyboard accessible
- Results announced via `aria-live`
- Screen reader: "Analysis complete, confidence 95%"
- Keyboard: Enter to upload, Tab to navigate

## Telemetry
- `document_analysis.view` — Screen loaded
- `document_analysis.upload` — Document uploaded
- `document_analysis.analyze` — Analysis started
- `document_analysis.export` — Results exported
- `document_analysis.save_kb` — Saved to knowledge base

## Implementation Notes
- Drag-and-drop upload
- Real-time analysis with progress
- Split pane for document + results
- AiDock provides analysis insights
- Batch processing for multiple documents
