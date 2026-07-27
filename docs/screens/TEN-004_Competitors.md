# TEN-004: Competitor Intelligence Screen Specification

**Module:** `features/competitors/CompetitorPage`
**Layer:** features
**Version:** 1.0.0
**Status:** Draft
**Workspace:** Acquisition

## Purpose
Competitor analysis, bid pattern intelligence, win/loss tracking, and strategic positioning for tender bidding.

## Screen Layout

```
┌─────────────────────────────────────────────────────────────┐
│ ExecutiveHeader                                             │
├──────────┬──────────────────────────────────────────────────┤
│          │ Breadcrumb: Acquisition > Competitors > {Tender} │
│ Workspace├──────────────────────────────────────────────────┤
│   Nav    │ CompetitorHeader (tender context)                │
│          ├──────────────────────────────────────────────────┤
│          │ CompetitorIntelligence (main content)            │
│          │ ┌────────────────────────────────────────────┐   │
│          │ │ CompetitorList (cards)                      │   │
│          │ │ ┌──────────────┐ ┌──────────────┐          │   │
│          │ │ │ Competitor 1 │ │ Competitor 2 │          │   │
│          │ │ │ Win Rate: 45%│ │ Win Rate: 32%│          │   │
│          │ │ │ Specialization│ │ Specialization│         │   │
│          │ │ └──────────────┘ └──────────────┘          │   │
│          │ ├────────────────────────────────────────────┤   │
│          │ │ BidHistory (table)                          │   │
│          │ │ Competitor | Date | Value | Result          │   │
│          │ │ ───────────────────────────────────────────│   │
│          │ │ ABC Corp  | 2025 | 50M   | Won             │   │
│          │ │ XYZ Ltd   | 2025 | 45M   | Lost            │   │
│          │ ├────────────────────────────────────────────┤   │
│          │ │ WinPatternAnalysis (chart)                  │   │
│          │ └────────────────────────────────────────────┘   │
├──────────┴──────────────────────────────────────────────────┤
│ AiDock (competitive strategy, bid recommendations)          │
└─────────────────────────────────────────────────────────────┘
```

## Component Tree

```
CompetitorPage
├── ExecutiveHeader
├── Breadcrumb
├── CompetitorHeader
│   ├── TenderCard (compact)
│   └── KpiStrip (competitor_count, avg_bid_ratio, win_probability)
├── CompetitorIntelligence
│   ├── CompetitorList
│   │   └── CompetitorCard × N
│   │       ├── Avatar (company logo)
│   │       ├── Badge (win_rate)
│   │       ├── Badge (specialization)
│   │       └── Button (View Profile)
│   ├── BidHistory
│   │   └── Table<CompetitorBid>
│   └── WinPatternAnalysis
│       └── Chart (scatter/bubble)
└── AiDock
    ├── AgentCard (Competitor Agent)
    └── EvidencePanel (strategy recommendations)
```

## Data Sources

### Competitor Profiles
```typescript
// API: GET /api/v1/competitors/{tender_id}
interface CompetitorList {
  tender_id: string;
  competitors: CompetitorProfile[];
  market_concentration: number;
  threat_level: 'low' | 'medium' | 'high';
}

interface CompetitorProfile {
  competitor_id: string;
  name: string;
  win_rate: number;
  avg_bid_ratio: number;
  total_bids: number;
  specializations: string[];
  zones: string[];
  agencies: string[];
  recent_activity: string;
  threat_score: number;
}
```

### Bid History
```typescript
// API: GET /api/v1/competitors/{competitor_id}/bids
interface BidHistory {
  competitor_id: string;
  bids: BidRecord[];
  win_patterns: WinPattern[];
}

interface BidRecord {
  tender_id: string;
  title: string;
  agency: string;
  bid_value: number;
  estimated_value: number;
  bid_ratio: number;
  result: 'won' | 'lost' | 'pending';
  submitted_at: string;
}

interface WinPattern {
  pattern: string;
  frequency: number;
  description: string;
}
```

### React Query
```typescript
const { data: competitors } = useQuery({
  queryKey: ['competitors', tenderId],
  queryFn: () => api.get(`/api/v1/competitors/${tenderId}`),
});

const { data: bidHistory } = useQuery({
  queryKey: ['competitors', competitorId, 'bids'],
  queryFn: () => api.get(`/api/v1/competitors/${competitorId}/bids`),
  enabled: !!competitorId,
});
```

## Zustand Store
```typescript
// stores/competitorStore.ts
interface CompetitorState {
  selectedCompetitor: string | null;
  sortBy: 'threat' | 'win_rate' | 'bid_ratio';
  filterZone: string | null;
  setSelected: (id: string | null) => void;
  setSort: (sort: string) => void;
  setZone: (zone: string | null) => void;
}
```

## Interactions

### Competitor Selection
1. Click CompetitorCard
2. Highlight in list
3. Show bid history for that competitor
4. AiDock shows strategy suggestions

### Bid History Analysis
1. Click bid record
2. Open TenderDetail drawer
3. Compare bid vs. estimated value
4. View win/loss details

### Win Pattern Analysis
1. View pattern chart
2. Click pattern for details
3. AI explains pattern significance
4. Apply insights to strategy

### Strategy Development
1. Select multiple competitors
2. Compare side-by-side
3. AiDock generates recommendations
4. Export competitor report

## Responsive Breakpoints

| Breakpoint | Layout |
|------------|--------|
| Desktop (>1024px) | 2-column (list + details) |
| Tablet (768-1024px) | Stacked with tabs |
| Mobile (<768px) | Full-screen list, swipe for details |

## Loading States
- CompetitorList: Skeleton cards
- BidHistory: Skeleton table
- Chart: Loading spinner

## Error States
- No competitors: EmptyState
- Data unavailable: Estimated values
- API error: Toast notification

## Accessibility
- Competitor cards are focusable
- Selection announced via `aria-live`
- Screen reader: "Competitor X, win rate Y%"
- Keyboard: Enter to select, Arrow keys to navigate

## Telemetry
- `competitor.view` — Screen loaded
- `competitor.select` — Competitor selected
- `competitor.bid_view` — Bid history viewed
- `competitor.strategy` — Strategy generated

## Implementation Notes
- CompetitorCard shows key metrics at a glance
- BidHistory table sortable and filterable
- WinPatternAnalysis uses Chart component
- AiDock provides competitive intelligence
- Export generates competitor report
