# OPP-002: Tender Qualification Screen Specification

**Module:** `features/qualification/QualificationPage`
**Layer:** features
**Version:** 1.0.0
**Status:** Draft
**Workspace:** Discovery

## Purpose
AI-assisted eligibility assessment and go/no-go decision for discovered tenders, with document analysis, financial criteria validation, and team collaboration.

## Screen Layout

```
┌─────────────────────────────────────────────────────────────┐
│ ExecutiveHeader                                             │
├──────────┬──────────────────────────────────────────────────┤
│          │ Breadcrumb: Discovery > Qualification > {Tender} │
│ Workspace├──────────────────────────────────────────────────┤
│   Nav    │ TenderSummary (card with key metrics)            │
│          ├──────────────────────────────────────────────────┤
│          │ QualificationWizard (Stepper + content)          │
│          │ ┌───────────────────────────────────────────┐    │
│          │ │ [1] Documents [2] Financial [3] Technical │    │
│          │ │ [4] Compliance [5] Decision               │    │
│          │ ├───────────────────────────────────────────┤    │
│          │ │                                           │    │
│          │ │ Step Content Area                         │    │
│          │ │ (varies by step)                          │    │
│          │ │                                           │    │
│          │ ├───────────────────────────────────────────┤    │
│          │ │ [Back] [Save Draft] [Next Step →]         │    │
│          │ └───────────────────────────────────────────┘    │
├──────────┴──────────────────────────────────────────────────┤
│ TrustPanel (AI confidence, document analysis status)        │
└─────────────────────────────────────────────────────────────┘
```

## Component Tree

```
QualificationPage
├── ExecutiveHeader
├── Breadcrumb
├── TenderSummary
│   ├── KpiCard (estimated_value)
│   ├── KpiCard (submission_deadline)
│   ├── KpiCard (ai_match_score)
│   └── ConfidenceBadge (qualification_score)
├── QualificationWizard
│   ├── Stepper (5 steps)
│   ├── Step1_Documents
│   │   ├── DocumentViewer (tender notice)
│   │   ├── DocumentViewer (TDS)
│   │   └── DocumentViewer (BOQ)
│   ├── Step2_Financial
│   │   ├── FinancialCriteriaTable
│   │   ├── EvidencePanel (document excerpts)
│   │   └── ConfidenceBadge (per criterion)
│   ├── Step3_Technical
│   │   ├── TechnicalRequirementsTable
│   │   └── ComplianceChecklist
│   ├── Step4_Compliance
│   │   ├── PPR2025Checklist
│   │   └── RiskAssessment
│   └── Step5_Decision
│       ├── GoNoGoForm
│       ├── CommentThread
│       └── Button (Submit Decision)
└── TrustPanel
```

## Data Sources

### Tender Details
```typescript
// API: GET /api/v1/tenders/{tender_id}
interface TenderDetails {
  tender_id: string;
  title: string;
  agency: string;
  estimated_value: number;
  submission_deadline: string;
  documents: Document[];
  qualification_status: 'pending' | 'in_progress' | 'qualified' | 'disqualified';
}
```

### TDS Extraction
```typescript
// API: GET /api/v1/document-ai/tds/{tender_id}
interface TDSExtraction {
  tender_id: string;
  financial_criteria: FinancialCriterion[];
  technical_requirements: TechnicalRequirement[];
  compliance_checklist: ComplianceItem[];
  extraction_confidence: number;
}

interface FinancialCriterion {
  criterion: string;
  required_value: number;
  unit: string;
  evidence: string;
  confidence: number;
  status: 'met' | 'not_met' | 'uncertain';
}
```

### Qualification Decision
```typescript
// API: POST /api/v1/tenders/{tender_id}/qualification
interface QualificationDecision {
  tender_id: string;
  decision: 'go' | 'no_go';
  financial_score: number;
  technical_score: number;
  compliance_score: number;
  overall_score: number;
  comments: string;
  decided_by: string;
  decided_at: string;
}
```

### React Query
```typescript
const { data: tender } = useQuery({
  queryKey: ['tender', tenderId],
  queryFn: () => api.get(`/api/v1/tenders/${tenderId}`),
});

const { data: tds } = useQuery({
  queryKey: ['tds', tenderId],
  queryFn: () => api.get(`/api/v1/document-ai/tds/${tenderId}`),
  enabled: !!tender,
});

const submitDecision = useMutation({
  mutationFn: (decision: QualificationDecision) =>
    api.post(`/api/v1/tenders/${tenderId}/qualification`, decision),
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ['tender', tenderId] });
    toast.success('Qualification decision submitted');
  },
});
```

## Zustand Store
```typescript
// stores/qualificationStore.ts
interface QualificationState {
  currentStep: number;
  draftDecision: Partial<QualificationDecision>;
  setStep: (step: number) => void;
  updateDraft: (updates: Partial<QualificationDecision>) => void;
  resetDraft: () => void;
}
```

## Interactions

### Step Navigation
1. Click step indicator to jump
2. "Next Step" validates current step
3. "Back" returns to previous step
4. Draft auto-saves on step change

### Document Review
1. Click document to open DocumentViewer
2. Highlight key sections automatically
3. Add comments/annotations
4. Mark as reviewed

### Financial Criteria
1. View required vs. available values
2. Evidence panel shows document excerpts
3. Toggle criterion status (met/not_met)
4. AI provides confidence score

### Go/No-Go Decision
1. Fill decision form
2. Add comments
3. Submit → POST API call
4. Redirect to Discovery or move to Acquisition

## Responsive Breakpoints

| Breakpoint | Layout |
|------------|--------|
| Desktop (>1024px) | Side-by-side document + criteria |
| Tablet (768-1024px) | Stacked with tabs |
| Mobile (<768px) | Full-screen wizard steps |

## Loading States
- Stepper: Skeleton steps
- DocumentViewer: PDF loading spinner
- Financial criteria: Skeleton table rows

## Error States
- Document load failure: Retry button
- Extraction failure: Manual entry fallback
- Submission failure: Save draft option

## Accessibility
- Step changes announced via `aria-live`
- Keyboard: Tab through steps, Enter to select
- Screen reader: Step X of Y, criterion status
- Focus management on step change

## Telemetry
- `qualification.view` — Screen loaded
- `qualification.step_change` — Step navigated
- `qualification.decision` — Go/No-Go submitted
- `qualification.document_view` — Document opened

## Implementation Notes
- 5-step wizard with draft persistence
- AI-powered document analysis
- Evidence panel shows source excerpts
- TrustPanel shows extraction confidence
- Comments for team collaboration
