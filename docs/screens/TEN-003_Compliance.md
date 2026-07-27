# TEN-003: Compliance Checker Screen Specification

**Module:** `features/compliance/CompliancePage`
**Layer:** features
**Version:** 1.0.0
**Status:** Draft
**Workspace:** Acquisition

## Purpose
PPR2025 compliance validation, document verification, regulatory checklist completion, and submission readiness assessment.

## Screen Layout

```
┌─────────────────────────────────────────────────────────────┐
│ ExecutiveHeader                                             │
├──────────┬──────────────────────────────────────────────────┤
│          │ Breadcrumb: Acquisition > Compliance > {Tender}  │
│ Workspace├──────────────────────────────────────────────────┤
│   Nav    │ ComplianceHeader (tender info, readiness score)  │
│          ├──────────────────────────────────────────────────┤
│          │ ComplianceChecker (main content)                 │
│          │ ┌────────────────────────────────────────────┐   │
│          │ │ Progress: ████████░░ 75% Complete          │   │
│          │ ├────────────────────────────────────────────┤   │
│          │ │ Checklist Items:                           │   │
│          │ │ [✓] Tender Notice verified                 │   │
│          │ │ [✓] TDS document present                   │   │
│          │ │ [✓] BOQ format validated                   │   │
│          │ │ [ ] Signing authority confirmed            │   │
│          │ │ [ ] Performance security calculated        │   │
│          │ │ [ ] Tender security amount set             │   │
│          │ │ [ ] Submission deadline noted              │   │
│          │ ├────────────────────────────────────────────┤   │
│          │ │ [Export Report] [Submit for Review]        │   │
│          │ └────────────────────────────────────────────┘   │
├──────────┴──────────────────────────────────────────────────┤
│ TrustPanel (compliance confidence, missing items)            │
└─────────────────────────────────────────────────────────────┘
```

## Component Tree

```
CompliancePage
├── ExecutiveHeader
├── Breadcrumb
├── ComplianceHeader
│   ├── TenderCard (compact)
│   └── ConfidenceBadge (readiness_score)
├── ComplianceChecker
│   ├── Progress (completion percentage)
│   ├── ComplianceChecklist
│   │   ├── ChecklistItem × N
│   │   │   ├── Checkbox
│   │   │   ├── Label
│   │   │   ├── EvidencePanel (document excerpt)
│   │   │   └── ConfidenceBadge (item confidence)
│   │   └── Button (Export Report)
│   └── Button (Submit for Review)
└── TrustPanel
```

## Data Sources

### Compliance Checklist
```typescript
// API: GET /api/v1/boq/{tender_id}/compliance
interface ComplianceChecklist {
  tender_id: string;
  items: ComplianceItem[];
  completion_pct: number;
  readiness_score: number;
  missing_items: string[];
}

interface ComplianceItem {
  id: string;
  category: string;
  description: string;
  status: 'verified' | 'pending' | 'missing' | 'not_applicable';
  confidence: number;
  evidence?: string;
  document_ref?: string;
  verified_by?: string;
  verified_at?: string;
  notes?: string;
}
```

### Verification Actions
```typescript
// API: POST /api/v1/boq/{tender_id}/compliance/{item_id}/verify
interface VerifyRequest {
  status: 'verified' | 'pending' | 'missing' | 'not_applicable';
  notes?: string;
  evidence?: string;
}

// API: POST /api/v1/boq/{tender_id}/compliance/submit
interface SubmitRequest {
  submitted_by: string;
  submission_notes: string;
}
```

### React Query
```typescript
const { data: checklist } = useQuery({
  queryKey: ['compliance', tenderId],
  queryFn: () => api.get(`/api/v1/boq/${tenderId}/compliance`),
});

const verifyItem = useMutation({
  mutationFn: ({ itemId, request }: { itemId: string; request: VerifyRequest }) =>
    api.post(`/api/v1/boq/${tenderId}/compliance/${itemId}/verify`, request),
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ['compliance', tenderId] });
  },
});

const submitCompliance = useMutation({
  mutationFn: (request: SubmitRequest) =>
    api.post(`/api/v1/boq/${tenderId}/compliance/submit`, request),
});
```

## Zustand Store
```typescript
// stores/complianceStore.ts
interface ComplianceState {
  expandedItems: Set<string>;
  filterStatus: 'all' | 'verified' | 'pending' | 'missing';
  toggleItem: (itemId: string) => void;
  setFilter: (status: string) => void;
}
```

## Interactions

### Item Verification
1. Click checklist item
2. Expand to show evidence
3. Toggle status (verified/pending/missing)
4. Add notes if needed
5. Auto-save on change

### Document Reference
1. Click document_ref link
2. Open DocumentViewer drawer
3. Highlight referenced section
4. Verify against checklist

### Export Report
1. Click Export Report
2. Generate compliance report
3. Download as PDF/Excel
4. Include all item statuses

### Submit for Review
1. Click Submit button
2. Validate all required items
3. Show confirmation modal
4. Submit via API
5. Redirect to dashboard

## Responsive Breakpoints

| Breakpoint | Layout |
|------------|--------|
| Desktop (>1024px) | Full checklist with evidence |
| Tablet (768-1024px) | Collapsible items |
| Mobile (<768px) | Stacked cards, bottom actions |

## Loading States
- Checklist: Skeleton items
- Progress: Skeleton bar
- Evidence: Loading spinner

## Error States
- Verification failure: Toast error
- Submission failure: Save draft
- Network error: Retry button

## Accessibility
- Checklist items are focusable
- Status changes announced via `aria-live`
- Screen reader: "Item X, status: verified"
- Keyboard: Space to toggle, Enter to expand

## Telemetry
- `compliance.view` — Screen loaded
- `compliance.verify` — Item verified
- `compliance.export` — Report exported
- `compliance.submit` — Submitted for review

## Implementation Notes
- Auto-save on item changes
- Evidence panel shows document excerpts
- TrustPanel shows overall confidence
- Export generates formatted report
- Submit validates all required items
