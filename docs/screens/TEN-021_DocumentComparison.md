# TEN-021: Document Comparison Screen Specification

**Module:** `features/document-comparison/DocumentComparisonPage`
**Layer:** features
**Version:** 1.0.0
**Status:** Draft
**Workspace:** Acquisition

## Purpose
Compare tender documents, highlight differences, and track changes.

## Screen Layout

```
┌─────────────────────────────────────────────────────────────┐
│ ExecutiveHeader                                             │
├──────────┬──────────────────────────────────────────────────┤
│          │ Breadcrumb: Acquisition > Document Comparison     │
│ Workspace├──────────────────────────────────────────────────┤
│   Nav    │ DocumentComparisonHeader (documents, version)    │
│          ├──────────────────────────────────────────────────┤
│          │ DocumentComparison (main content)                │
│          │ ┌────────────────────────────────────────────┐   │
│          │ │ SplitView (side-by-side)                    │   │
│          │ │ ┌──────────────┬──────────────┐            │   │
│          │ │ │ Document A   │ Document B   │            │   │
│          │ │ │              │              │            │   │
│          │ │ │              │              │            │   │
│          │ │ └──────────────┴──────────────┘            │   │
│          │ ├────────────────────────────────────────────┤   │
│          │ │ DiffSummary (changes overview)              │   │
│          │ └────────────────────────────────────────────┘   │
├──────────┴──────────────────────────────────────────────────┤
│ AiDock (document insights)                                  │
└─────────────────────────────────────────────────────────────┘
```

## Component Tree

```
DocumentComparisonPage
├── ExecutiveHeader
├── Breadcrumb
├── DocumentComparisonHeader
│   ├── DocumentSelector (left document)
│   ├── DocumentSelector (right document)
│   └── Button (Export Diff)
├── DocumentComparison
│   ├── SplitView
│   │   ├── DocumentPanel
│   │   │   ├── document_info
│   │   │   └── content
│   │   └── DocumentPanel
│   │       ├── document_info
│   │       └── content
│   ├── DiffHighlight
│   │   ├── added
│   │   ├── removed
│   │   └── modified
│   ├── DiffSummary
│   │   ├── changes_count
│   │   ├── additions
│   │   ├── deletions
│   │   └── modifications
│   └── ChangeList
│       └── ChangeItem × N
│           ├── type
│           ├── location
│           ├── old_value
│           └── new_value
└── AiDock
    ├── AgentCard (Document Agent)
    └── EvidencePanel (document insights)
```

## Data Sources

### Document Comparison
```typescript
// API: GET /api/v1/documents/compare
interface DocumentComparison {
  document_a: Document;
  document_b: Document;
  changes: Change[];
  summary: DiffSummary;
}

interface Document {
  document_id: string;
  name: string;
  version: string;
  content: string;
}

interface Change {
  change_id: string;
  type: 'added' | 'removed' | 'modified';
  location: string;
  old_value?: string;
  new_value?: string;
}

interface DiffSummary {
  total_changes: number;
  additions: number;
  deletions: number;
  modifications: number;
}
```

### React Query
```typescript
const { data: comparison } = useQuery({
  queryKey: ['documents', 'compare', docA, docB],
  queryFn: () => api.get('/api/v1/documents/compare', { params: { document_a: docA, document_b: docB } }),
  enabled: !!docA && !!docB,
});
```

## Zustand Store
```typescript
// stores/documentComparisonStore.ts
interface DocumentComparisonState {
  selectedDocumentA: string | null;
  selectedDocumentB: string | null;
  setDocumentA: (id: string | null) => void;
  setDocumentB: (id: string | null) => void;
}
```

## Interactions

### Select Documents
1. Choose left document
2. Choose right document
3. Load comparison
4. Display diff

### Navigate Changes
1. Click change in list
2. Jump to location
3. View context
4. Highlight diff

### Export Diff
1. Click Export
2. Choose format
3. Include all changes
4. Download file

### Filter Changes
1. Select change type
2. Filter list
3. Update view
4. Preserve selection

## Responsive Breakpoints

| Breakpoint | Layout |
|------------|--------|
| Desktop (>1024px) | Full split view |
| Tablet (768-1024px) | Stacked panels |
| Mobile (<768px) | Single document |

## Loading States
- Comparison: Loading split view
- Changes: Skeleton list
- Export: Loading spinner

## Error States
- Load failure: Retry button
- No changes: EmptyState
- Network error: Toast notification

## Accessibility
- Changes are focusable
- Navigation announced via `aria-live`
- Screen reader: "Change 1 of 10: Added line 5"
- Keyboard: Arrow keys to navigate

## Telemetry
- `document_comparison.view` — Screen loaded
- `document_comparison.select` — Documents selected
- `document_comparison.navigate` — Change navigated
- `document_comparison.export` — Diff exported

## Implementation Notes
- Side-by-side document comparison
- Diff highlighting
- Change navigation
- AiDock provides document insights
- Export for review
