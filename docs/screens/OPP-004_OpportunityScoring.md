# OPP-004: Opportunity Scoring Screen Specification

**Module:** `features/opportunity-scoring/OpportunityScoringPage`
**Layer:** features
**Version:** 1.0.0
**Status:** Draft
**Workspace:** Discovery

## Purpose
AI-powered opportunity scoring, tender ranking, and prioritization for bid/no-bid decisions.

## Screen Layout

```
┌─────────────────────────────────────────────────────────────┐
│ ExecutiveHeader                                             │
├──────────┬──────────────────────────────────────────────────┤
│          │ Breadcrumb: Discovery > Opportunity Scoring       │
│ Workspace├──────────────────────────────────────────────────┤
│   Nav    │ OpportunityScoringHeader (filters, sort)         │
│          ├──────────────────────────────────────────────────┤
│          │ OpportunityScoring (main content)                │
│          │ ┌────────────────────────────────────────────┐   │
│          │ │ ScoringResults (ranked list)                │   │
│          │ │ ┌──────────────────────────────────────────┐│   │
│          │ │ │ 1. Tender A    Score: 92  [Analyze]      ││   │
│          │ │ │ 2. Tender B    Score: 87  [Analyze]      ││   │
│          │ │ │ 3. Tender C    Score: 81  [Analyze]      ││   │
│          │ │ │ ...                                      ││   │
│          │ │ └──────────────────────────────────────────┘│   │
│          │ ├────────────────────────────────────────────┤   │
│          │ │ ScoringFactors (factor breakdown)          │   │
│          │ │ Agency, Zone, Value, Deadline, Match       │   │
│          │ └────────────────────────────────────────────┘   │
├──────────┴──────────────────────────────────────────────────┤
│ AiDock (scoring insights, prioritization)                   │
└─────────────────────────────────────────────────────────────┘
```

## Component Tree

```
OpportunityScoringPage
├── ExecutiveHeader
├── Breadcrumb
├── OpportunityScoringHeader
│   ├── ChipSelect (agencies)
│   ├── ChipSelect (zones)
│   ├── RangeSlider (min_score)
│   └── SortDropdown (score, value, deadline)
├── OpportunityScoring
│   ├── ScoringResults
│   │   └── VirtualList<ScoredTender>
│   │       └── ScoredCard × N
│   │           ├── rank
│   │           ├── TenderCard (compact)
│   │           ├── ConfidenceBadge (score)
│   │           ├── factor_bars
│   │           └── Button (Analyze)
│   └── ScoringFactors
│       ├── FactorCard × N
│       │   ├── name
│       │   ├── weight
│       │   ├── score
│       │       └── Sparkline (trend)
│       └── TotalScore (gauge)
└── AiDock
    ├── AgentCard (Discovery Agent)
    └── EvidencePanel (scoring insights)
```

## Data Sources

### Scored Tenders
```typescript
// API: POST /api/v1/tenders/score
interface ScoredTenderList {
  tenders: ScoredTender[];
  total_count: number;
  scoring_model: string;
}

interface ScoredTender {
  tender_id: string;
  title: string;
  agency: string;
  zone: string;
  estimated_value: number;
  submission_deadline: string;
  score: number;
  rank: number;
  factors: ScoringFactor[];
}

interface ScoringFactor {
  name: string;
  weight: number;
  score: number;
  max_score: number;
  description: string;
}

interface ScoreRequest {
  agencies?: string[];
  zones?: string[];
  min_score?: number;
  sort_by?: 'score' | 'value' | 'deadline';
  limit?: number;
}
```

### React Query
```typescript
const { data: scoredTenders } = useQuery({
  queryKey: ['tenders', 'score', filters],
  queryFn: () => api.post('/api/v1/tenders/score', filters),
});

const analyzeTender = useMutation({
  mutationFn: (tenderId: string) =>
    api.post(`/api/v1/tenders/${tenderId}/analyze`),
  onSuccess: () => {
    toast.success('Analysis started');
  },
});
```

## Zustand Store
```typescript
// stores/opportunityScoringStore.ts
interface OpportunityScoringState {
  filters: ScoreRequest;
  selectedTender: string | null;
  setFilter: <K extends keyof ScoreRequest>(key: K, value: ScoreRequest[K]) => void;
  setSelected: (id: string | null) => void;
}
```

## Interactions

### Score Tenders
1. Apply filters
2. Run scoring model
3. View ranked results
4. Analyze factors

### Analyze Tender
1. Click "Analyze" button
2. Start detailed analysis
3. View full scoring breakdown
4. Make bid/no-bid decision

### Adjust Factors
1. View scoring factors
2. Analyze weights
3. Understand scoring logic
4. Provide feedback

### Prioritize
1. Sort by score/value/deadline
2. Filter by minimum score
3. Create shortlist
4. Export priorities

## Responsive Breakpoints

| Breakpoint | Layout |
|------------|--------|
| Desktop (>1024px) | Full list + factors |
| Tablet (768-1024px) | Stacked view |
| Mobile (<768px) | Card view, swipe |

## Loading States
- Scoring: Progress indicator
- Results: Skeleton cards
- Factors: Skeleton bars

## Error States
- Scoring failure: Retry button
- No results: EmptyState
- Network error: Toast notification

## Accessibility
- Cards are focusable
- Scores announced via `aria-live`
- Screen reader: "Tender A, score 92"
- Keyboard: Enter to analyze, Arrow to navigate

## Telemetry
- `opportunity_scoring.view` — Screen loaded
- `opportunity_scoring.score` — Scoring run
- `opportunity_scoring.analyze` — Tender analyzed
- `opportunity_scoring.export` — Results exported

## Implementation Notes
- AI-powered scoring model
- Multi-factor analysis
- Ranked results with visualization
- AiDock provides scoring insights
- Export for prioritization
