# OPP-017: Market Intelligence Screen Specification

**Module:** `features/market-intelligence/MarketIntelligencePage`
**Layer:** features
**Version:** 1.0.0
**Status:** Draft
**Workspace:** Opportunity

## Purpose
Gather, analyze, and present market intelligence and competitive insights.

## Screen Layout

```
┌─────────────────────────────────────────────────────────────┐
│ ExecutiveHeader                                             │
├──────────┬──────────────────────────────────────────────────┤
│          │ Breadcrumb: Opportunity > Market Intelligence     │
│ Workspace├──────────────────────────────────────────────────┤
│   Nav    │ MarketIntelligenceHeader (insights, sources)     │
│          ├──────────────────────────────────────────────────┤
│          │ MarketIntelligence (main content)                │
│          │ ┌────────────────────────────────────────────┐   │
│          │ │ Tabs: [Overview] [Competitors] [Trends]     │   │
│          │ ├────────────────────────────────────────────┤   │
│          │ │ OverviewTab (market summary)                │   │
│          │ │ CompetitorsTab (competitor analysis)        │   │
│          │ │ TrendsTab (market trends)                   │   │
│          │ └────────────────────────────────────────────┘   │
├──────────┴──────────────────────────────────────────────────┤
│ AiDock (intelligence insights)                              │
└─────────────────────────────────────────────────────────────┘
```

## Component Tree

```
MarketIntelligencePage
├── ExecutiveHeader
├── Breadcrumb
├── MarketIntelligenceHeader
│   ├── KpiStrip (insight_count, source_count, confidence)
│   └── Button (Refresh Intelligence)
├── MarketIntelligence
│   ├── Tabs
│   │   ├── OverviewTab
│   │   │   ├── MarketSummary
│   │   │   │   ├── market_size
│   │   │   │   ├── growth_rate
│   │   │   │   └── key_players
│   │   │   ├── Chart (market_trends)
│   │   │   └── Chart (opportunity_distribution)
│   │   ├── CompetitorsTab
│   │   │   └── CompetitorList
│   │   │       └── CompetitorCard × N
│   │   │           ├── name
│   │   │           ├── market_share
│   │   │           ├── strengths
│   │   │           ├── weaknesses
│   │   │           └── Button (View Details)
│   │   └── TrendsTab
│   │       └── TrendList
│   │           └── TrendCard × N
│   │               ├── name
│   │               ├── direction
│   │               ├── impact
│   │               └── Button (Analyze)
│   ├── InsightFeed
│   │   └── Insight × N
│   │       ├── title
│   │       ├── source
│   │       ├── relevance
│   │       └── timestamp
│   └── IntelligenceReport
│       ├── executive_summary
│       ├── key_findings
│       └── recommendations
└── AiDock
    ├── AgentCard (Intelligence Agent)
    └── EvidencePanel (intelligence insights)
```

## Data Sources

### Market Intelligence
```typescript
// API: GET /api/v1/opportunities/intelligence
interface MarketIntelligence {
  overview: MarketOverview;
  competitors: Competitor[];
  trends: MarketTrend[];
  insights: Insight[];
}

interface MarketOverview {
  market_size: number;
  growth_rate: number;
  key_players: string[];
  recent_developments: string[];
}

interface Competitor {
  competitor_id: string;
  name: string;
  market_share: number;
  strengths: string[];
  weaknesses: string[];
  recent_activity: string[];
}

interface MarketTrend {
  trend_id: string;
  name: string;
  direction: 'up' | 'down' | 'stable';
  impact: 'high' | 'medium' | 'low';
  description: string;
}

interface Insight {
  insight_id: string;
  title: string;
  source: string;
  relevance: number;
  summary: string;
  published_at: string;
}
```

### React Query
```typescript
const { data: intelligence } = useQuery({
  queryKey: ['opportunities', 'intelligence'],
  queryFn: () => api.get('/api/v1/opportunities/intelligence'),
});
```

## Zustand Store
```typescript
// stores/marketIntelligenceStore.ts
interface MarketIntelligenceState {
  activeTab: string;
  setTab: (tab: string) => void;
}
```

## Interactions

### View Overview
1. Click Overview tab
2. View market summary
3. Check trends
4. Review opportunities

### Analyze Competitors
1. Click Competitors tab
2. View competitor cards
3. Check market share
4. Review strengths/weaknesses

### Track Trends
1. Click Trends tab
2. View trend cards
3. Check direction
4. Analyze impact

### Read Insights
1. View insight feed
2. Read summaries
3. Check sources
4. Take action

## Responsive Breakpoints

| Breakpoint | Layout |
|------------|--------|
| Desktop (>1024px) | Full tabs + panels |
| Tablet (768-1024px) | Stacked tabs |
| Mobile (<768px) | Simplified view |

## Loading States
- Intelligence: Loading data
- Competitors: Loading cards
- Trends: Loading list

## Error States
- Load failure: Retry button
- Refresh failure: Toast error
- Network error: Toast notification

## Accessibility
- Insights are focusable
- Trends announced via `aria-live`
- Screen reader: "Trend: Infrastructure growth, direction: up"
- Keyboard: Tab through insights

## Telemetry
- `market_intelligence.view` — Screen loaded
- `market_intelligence.refresh` — Intelligence refreshed
- `market_intelligence.analyze` — Competitor analyzed

## Implementation Notes
- Market intelligence gathering
- Competitor analysis
- Trend tracking
- AiDock provides intelligence insights
- Export for decision making
