# TEN-018: Award Analysis Screen Specification

**Module:** `features/award-analysis/AwardAnalysisPage`
**Layer:** features
**Version:** 1.0.0
**Status:** Draft
**Workspace:** Acquisition

## Purpose
Award outcome analysis, win/loss patterns, and competitive intelligence.

## Screen Layout

```
┌─────────────────────────────────────────────────────────────┐
│ ExecutiveHeader                                             │
├──────────┬──────────────────────────────────────────────────┤
│          │ Breadcrumb: Acquisition > Award Analysis          │
│ Workspace├──────────────────────────────────────────────────┤
│   Nav    │ AwardAnalysisHeader (period, filters)            │
│          ├──────────────────────────────────────────────────┤
│          │ AwardAnalysis (main content)                     │
│          │ ┌────────────────────────────────────────────┐   │
│          │ │ KpiStrip (award metrics)                    │   │
│          │ ├────────────────────────────────────────────┤   │
│          │ │ Tabs: [Outcomes] [Competitors] [Trends]    │   │
│          │ │ [Insights]                                  │   │
│          │ ├────────────────────────────────────────────┤   │
│          │ │ AwardOutcomes (win/loss breakdown)          │   │
│          │ │ CompetitorAnalysis (bid comparisons)        │   │
│          │ │ TrendAnalysis (historical patterns)         │   │
│          │ │ AiInsights (recommendations)                │   │
│          │ └────────────────────────────────────────────┘   │
├──────────┴──────────────────────────────────────────────────┤
│ AiDock (award insights, competitive intelligence)           │
└─────────────────────────────────────────────────────────────┘
```

## Component Tree

```
AwardAnalysisPage
├── ExecutiveHeader
├── Breadcrumb
├── AwardAnalysisHeader
│   ├── CalendarRange (period)
│   ├── ChipSelect (agencies)
│   ├── ChipSelect (zones)
│   └── Button (Export Report)
├── AwardAnalysis
│   ├── KpiStrip
│   │   ├── KpiCard (total_awards)
│   │   ├── KpiCard (win_rate)
│   │   ├── KpiCard (avg_award_value)
│   │   └── KpiCard (total_award_value)
│   ├── Tabs
│   │   ├── OutcomesTab
│   │   │   └── AwardOutcomes
│   │   │       ├── Chart (win_loss_ratio)
│   │   │       ├── Chart (by_agency)
│   │   │       ├── Chart (by_zone)
│   │   │       └── Table (outcome_details)
│   │   ├── CompetitorsTab
│   │   │   └── CompetitorAnalysis
│   │   │       ├── CompetitorMatrix
│   │   │       ├── CompetitorCard × N
│   │   │       │   ├── name
│   │   │       │   ├── win_rate
│   │   │       │   └── avg_bid_ratio
│   │   │       └── Chart (competitive_landscape)
│   │   ├── TrendsTab
│   │   │   └── TrendAnalysis
│   │   │       ├── Chart (award_trends)
│   │   │       ├── Chart (value_trends)
│   │   │       └── AiInsight × N
│   │   └── InsightsTab
│   │       └── AiInsights
│   │           ├── InsightCard × N
│   │           │   ├── type
│   │           │   ├── title
│   │           │   ├── description
│   │           │   └── ConfidenceBadge
│   │           └── RecommendationList
│   └── AwardSummary
│       ├── KpiCard (longest_win_streak)
│       ├── KpiCard (biggest_win)
│       └── KpiCard (avg_margin)
└── AiDock
    ├── AgentCard (Intelligence Agent)
    └── EvidencePanel (award insights)
```

## Data Sources

### Award Analysis
```typescript
// API: GET /api/v1/pricing/awards/analysis
interface AwardAnalysis {
  stats: AwardStats;
  outcomes: AwardOutcome[];
  competitors: CompetitorAnalysis[];
  trends: AwardTrend[];
  insights: AiInsight[];
}

interface AwardStats {
  total_awards: number;
  wins: number;
  losses: number;
  win_rate: number;
  avg_award_value: number;
  total_award_value: number;
}

interface AwardOutcome {
  tender_id: string;
  title: string;
  agency: string;
  zone: string;
  bid_value: number;
  award_value: number;
  status: 'won' | 'lost';
  margin?: number;
}

interface CompetitorAnalysis {
  competitor_id: string;
  name: string;
  win_rate: number;
  avg_bid_ratio: number;
  total_bids: number;
}

interface AwardTrend {
  period: string;
  awards: number;
  wins: number;
  value: number;
}
```

### React Query
```typescript
const { data: analysis } = useQuery({
  queryKey: ['pricing', 'awards', 'analysis', period],
  queryFn: () => api.get('/api/v1/pricing/awards/analysis', { params: period }),
  refetchInterval: 300_000, // 5 minutes
});
```

## Zustand Store
```typescript
// stores/awardAnalysisStore.ts
interface AwardAnalysisState {
  period: { start: string; end: string };
  setPeriod: (period: { start: string; end: string }) => void;
}
```

## Interactions

### View Outcomes
1. Click Outcomes tab
2. View win/loss ratio
3. Analyze by agency/zone
4. Review details

### Analyze Competitors
1. Click Competitors tab
2. View competitor matrix
3. Compare win rates
4. Identify patterns

### View Trends
1. Click Trends tab
2. View historical patterns
3. Read AI insights
4. Predict future

### View Insights
1. Click Insights tab
2. Read AI recommendations
3. Review confidence scores
4. Take action

## Responsive Breakpoints

| Breakpoint | Layout |
|------------|--------|
| Desktop (>1024px) | Full tabs with charts |
| Tablet (768-1024px) | Stacked tabs |
| Mobile (<768px) | Single tab view |

## Loading States
- KPIs: Skeleton cards
- Charts: Skeleton with shimmer
- Insights: Skeleton cards

## Error States
- Load failure: Retry button
- Export failure: Toast error
- Network error: Toast notification

## Accessibility
- KPIs announced via `aria-live`
- Charts have table fallback
- Screen reader: "Win rate: 45%"
- Keyboard: Tab through elements

## Telemetry
- `award_analysis.view` — Screen loaded
- `award_analysis.tab_switch` — Tab changed
- `award_analysis.export` — Report exported

## Implementation Notes
- Award outcome analysis
- Competitive intelligence
- Historical trend analysis
- AiDock provides award insights
- Export for strategic planning
