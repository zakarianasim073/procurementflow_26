# TEN-030: Tender Evaluation Screen Specification

**Module:** `features/tender-evaluation/TenderEvaluationPage`
**Layer:** features
**Version:** 1.0.0
**Status:** Draft
**Workspace:** Acquisition

## Purpose
Evaluate tenders, score proposals, and make award decisions.

## Screen Layout

```
┌─────────────────────────────────────────────────────────────┐
│ ExecutiveHeader                                             │
├──────────┬──────────────────────────────────────────────────┤
│          │ Breadcrumb: Acquisition > Tender Evaluation       │
│ Workspace├──────────────────────────────────────────────────┤
│   Nav    │ TenderEvaluationHeader (tender, status)          │
│          ├──────────────────────────────────────────────────┤
│          │ TenderEvaluation (main content)                  │
│          │ ┌────────────────────────────────────────────┐   │
│          │ │ EvaluationBoard (scoring matrix)            │   │
│          │ │ ┌──────────────────────────────────────────┐│   │
│          │ │ │ Criteria  │ Weight │ Bidder A │ Bidder B ││   │
│          │ │ │ Technical │  40%   │   35     │   30     ││   │
│          │ │ │ Financial │  60%   │   50     │   55     ││   │
│          │ │ └──────────────────────────────────────────┘│   │
│          │ ├────────────────────────────────────────────┤   │
│          │ │ EvaluationResults (final scores)            │   │
│          │ └────────────────────────────────────────────┘   │
├──────────┴──────────────────────────────────────────────────┤
│ AiDock (evaluation insights)                                │
└─────────────────────────────────────────────────────────────┘
```

## Component Tree

```
TenderEvaluationPage
├── ExecutiveHeader
├── Breadcrumb
├── TenderEvaluationHeader
│   ├── KpiStrip (bid_count, evaluated_count, recommended)
│   └── Button (Finalize Evaluation)
├── TenderEvaluation
│   ├── EvaluationBoard
│   │   ├── CriteriaList
│   │   │   └── Criteria × N
│   │   │       ├── name
│   │   │       ├── weight
│   │   │       ├── description
│   │   │       └── ScoreInput × N
│   │   │           ├── bidder
│   │   │           ├── score
│   │   │           └── comments
│   │   └── WeightAdjustment
│   │       └── WeightSlider × N
│   │           ├── criteria
│   │           └── weight
│   ├── EvaluationResults
│   │   ├── ScoreBoard
│   │   │   └── BidderScore × N
│   │   │       ├── bidder
│   │   │       ├── total_score
│   │   │       ├── rank
│   │   │       └── Button (View Details)
│   │   └── RecommendationCard
│   │       ├── recommended_bidder
│   │       ├── justification
│   │       └── risk_assessment
│   ├── EvaluationComments
│   │   └── Comment × N
│   │       ├── evaluator
│   │       ├── criteria
│   │       ├── comment
│   │       └── timestamp
│   └── EvaluationHistory
│       └── HistoryEntry × N
│           ├── action
│           ├── user
│           └── timestamp
└── AiDock
    ├── AgentCard (Evaluation Agent)
    └── EvidencePanel (evaluation insights)
```

## Data Sources

### Tender Evaluation
```typescript
// API: GET /api/v1/tenders/{tender_id}/evaluation
interface TenderEvaluation {
  tender_id: string;
  criteria: Criteria[];
  scores: EvaluationScore[];
  recommendation: Recommendation;
  history: EvaluationHistory[];
}

interface Criteria {
  criteria_id: string;
  name: string;
  description: string;
  weight: number;
  max_score: number;
}

interface EvaluationScore {
  bid_id: string;
  bidder_name: string;
  scores: Record<string, number>; // criteria_id -> score
  total_score: number;
  rank: number;
}

interface Recommendation {
  recommended_bidder: string;
  total_score: number;
  justification: string;
  risk_level: 'low' | 'medium' | 'high';
  risks: string[];
}

interface EvaluationHistory {
  entry_id: string;
  action: string;
  user_id: string;
  user_name: string;
  timestamp: string;
  details?: Record<string, any>;
}
```

### React Query
```typescript
const { data: evaluation } = useQuery({
  queryKey: ['tenders', tenderId, 'evaluation'],
  queryFn: () => api.get(`/api/v1/tenders/${tenderId}/evaluation`),
  enabled: !!tenderId,
});

const updateScore = useMutation({
  mutationFn: ({ tenderId, bidId, criteriaId, score }: UpdateScoreRequest) =>
    api.put(`/api/v1/tenders/${tenderId}/evaluation/scores`, { bid_id: bidId, criteria_id: criteriaId, score }),
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ['tenders', tenderId, 'evaluation'] });
    toast.success('Score updated');
  },
});

const finalizeEvaluation = useMutation({
  mutationFn: (tenderId: string) => api.post(`/api/v1/tenders/${tenderId}/evaluation/finalize`),
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ['tenders', tenderId, 'evaluation'] });
    toast.success('Evaluation finalized');
  },
});
```

## Zustand Store
```typescript
// stores/tenderEvaluationStore.ts
interface TenderEvaluationState {
  selectedBidder: string | null;
  setBidder: (id: string | null) => void;
}
```

## Interactions

### Input Score
1. Select criteria
2. Select bidder
3. Enter score
4. Add comments

### Adjust Weight
1. Select criteria
2. Adjust weight slider
3. Update scores
4. Recalculate totals

### View Results
1. View scoreboard
2. Check rankings
3. Read recommendation
4. Review risks

### Finalize
1. Review all scores
2. Check completeness
3. Confirm evaluation
4. Submit decision

## Responsive Breakpoints

| Breakpoint | Layout |
|------------|--------|
| Desktop (>1024px) | Full evaluation board |
| Tablet (768-1024px) | Simplified board |
| Mobile (<768px) | Mobile-friendly view |

## Loading States
- Evaluation: Loading board
- Scores: Saving indicator
- Results: Loading scoreboard

## Error States
- Save failure: Toast error
- Finalize failure: Error details
- Network error: Toast notification

## Accessibility
- Scores are focusable
- Updates announced via `aria-live`
- Screen reader: "Bidder A: Total score 85"
- Keyboard: Tab through inputs

## Telemetry
- `tender_evaluation.view` — Screen loaded
- `tender_evaluation.score_update` — Score updated
- `tender_evaluation.finalize` — Evaluation finalized

## Implementation Notes
- Scoring matrix
- Weight adjustment
- Real-time calculation
- AiDock provides evaluation insights
- Audit trail
