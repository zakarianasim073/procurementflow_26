# TEN-006: Bid Submission Screen Specification

**Module:** `features/submission/SubmissionPage`
**Layer:** features
**Version:** 1.0.0
**Status:** Draft
**Workspace:** Acquisition

## Purpose
Final bid preparation, document assembly, review workflow, and submission to e-GP portal.

## Screen Layout

```
┌─────────────────────────────────────────────────────────────┐
│ ExecutiveHeader                                             │
├──────────┬──────────────────────────────────────────────────┤
│          │ Breadcrumb: Acquisition > Submission > {Tender}  │
│ Workspace├──────────────────────────────────────────────────┤
│   Nav    │ SubmissionHeader (tender info, deadline)         │
│          ├──────────────────────────────────────────────────┤
│          │ SubmissionWizard (main content)                  │
│          │ ┌────────────────────────────────────────────┐   │
│          │ │ [1] Documents [2] Pricing [3] Review       │   │
│          │ │ [4] Compliance [5] Submit                   │   │
│          │ ├────────────────────────────────────────────┤   │
│          │ │ Step Content Area                          │   │
│          │ │ (varies by step)                           │   │
│          │ ├────────────────────────────────────────────┤   │
│          │ │ [Back] [Save Draft] [Next Step →]          │   │
│          │ └────────────────────────────────────────────┘   │
├──────────┴──────────────────────────────────────────────────┤
│ AiDock (submission checklist, final review)                 │
└─────────────────────────────────────────────────────────────┘
```

## Component Tree

```
SubmissionPage
├── ExecutiveHeader
├── Breadcrumb
├── SubmissionHeader
│   ├── TenderCard (compact)
│   └── KpiStrip (deadline, completeness, readiness)
├── SubmissionWizard
│   ├── Stepper (5 steps)
│   ├── Step1_Documents
│   │   ├── DocumentList
│   │   │   └── DocumentCard × N
│   │   └── FileUpload (additional docs)
│   ├── Step2_Pricing
│   │   ├── BidSummary
│   │   └── PriceBreakdown
│   ├── Step3_Review
│   │   ├── ComplianceChecklist
│   │   └── EvidencePanel
│   ├── Step4_Compliance
│   │   ├── FinalChecklist
│   │   └── ApprovalForm
│   └── Step5_Submit
│       ├── SubmissionForm
│       └── Button (Submit to e-GP)
└── AiDock
    ├── AgentCard (Decision Agent)
    └── EvidencePanel (submission checklist)
```

## Data Sources

### Submission Data
```typescript
// API: GET /api/v1/tenders/{tender_id}/submission
interface SubmissionData {
  tender_id: string;
  status: 'draft' | 'ready' | 'submitted';
  documents: SubmissionDocument[];
  pricing: BidComposition;
  compliance: ComplianceChecklist;
  completeness_pct: number;
  readiness_score: number;
}

interface SubmissionDocument {
  document_id: string;
  type: string;
  name: string;
  status: 'ready' | 'missing' | 'pending_review';
  file_url?: string;
}
```

### Submit Bid
```typescript
// API: POST /api/v1/tenders/{tender_id}/submit
interface SubmitBidRequest {
  documents: string[];
  pricing_confirmed: boolean;
  compliance_confirmed: boolean;
  submitted_by: string;
  submission_notes?: string;
}

interface SubmitBidResponse {
  submission_id: string;
  status: 'submitted' | 'failed';
  eGP_reference?: string;
  submitted_at: string;
  error?: string;
}
```

### React Query
```typescript
const { data: submission } = useQuery({
  queryKey: ['tenders', tenderId, 'submission'],
  queryFn: () => api.get(`/api/v1/tenders/${tenderId}/submission`),
});

const submitBid = useMutation({
  mutationFn: (request: SubmitBidRequest) =>
    api.post(`/api/v1/tenders/${tenderId}/submit`, request),
  onSuccess: (response) => {
    queryClient.invalidateQueries({ queryKey: ['tenders', tenderId] });
    if (response.status === 'submitted') {
      toast.success('Bid submitted successfully');
      navigate(`/acquisition/${tenderId}/confirmation`);
    } else {
      toast.error(`Submission failed: ${response.error}`);
    }
  },
});
```

## Zustand Store
```typescript
// stores/submissionStore.ts
interface SubmissionState {
  currentStep: number;
  draftSubmission: Partial<SubmitBidRequest>;
  isSubmitting: boolean;
  setStep: (step: number) => void;
  updateDraft: (updates: Partial<SubmitBidRequest>) => void;
  setIsSubmitting: (submitting: boolean) => void;
}
```

## Interactions

### Document Upload
1. Drag files to upload zone
2. Or click to browse
3. Show upload progress
4. Update document status

### Step Navigation
1. Click step indicator
2. Validate current step
3. Save draft
4. Navigate to step

### Final Review
1. Review all sections
2. Check completeness
3. Confirm pricing
4. Acknowledge compliance

### Submit to e-GP
1. Click Submit button
2. Show confirmation modal
3. Confirm submission
4. POST to API
5. Show result (success/failure)
6. Redirect to confirmation

## Responsive Breakpoints

| Breakpoint | Layout |
|------------|--------|
| Desktop (>1024px) | Full wizard with sidebar |
| Tablet (768-1024px) | Stacked wizard steps |
| Mobile (<768px) | Single step view |

## Loading States
- Documents: Skeleton list
- Pricing: Skeleton summary
- Compliance: Skeleton checklist

## Error States
- Upload failure: Retry button
- Submission failure: Save draft
- e-GP error: Contact support

## Accessibility
- Step changes announced via `aria-live`
- Keyboard: Tab through steps, Enter to select
- Screen reader: "Step X of Y"
- Focus management on step change

## Telemetry
- `submission.view` — Screen loaded
- `submission.step_change` — Step navigated
- `submission.document_upload` — Document uploaded
- `submission.submit` — Bid submitted

## Implementation Notes
- 5-step wizard with draft persistence
- Document upload with progress
- Final review before submission
- e-GP integration via API
- AiDock provides submission checklist
