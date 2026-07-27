# KNOW-006: Market Intelligence Screen Specification

**Module:** `features/market-intelligence/MarketIntelligencePage`
**Layer:** features
**Version:** 1.0.0
**Status:** Draft
**Workspace:** Knowledge

## Purpose
Deep market intelligence, trend analysis, competitive landscape, and strategic insights.

## Screen Layout

```
┌─────────────────────────────────────────────────────────────┐
│ ExecutiveHeader                                             │
├──────────┬──────────────────────────────────────────────────┤
│          │ Breadcrumb: Knowledge > Market Intelligence       │
│ Workspace├──────────────────────────────────────────────────┤
│   Nav    │ MarketIntelligenceHeader (date range, filters)   │
│          ├──────────────────────────────────────────────────┤
│          │ MarketIntelligence (main content)                │
│          │ ┌────────────────────────────────────────────┐   │
│          │ │ Tabs: [Trends] [Competitors] [Agencies]    │   │
│          │ │ [Zones] [Insights]                          │   │
│          │ ├────────────────────────────────────────────┤   │
│          │ │ TrendAnalysis (charts + insights)          │   │
│          │ │ CompetitorLandscape (profiles + matrix)    │   │
│          │ │ AgencyAnalytics (performance + rankings)   │   │
│          │ │ ZoneIntelligence (geographic + heatmap)    │   │
│          │ │ AiInsights (recommendations + predictions) │   │
│          │ └────────────────────────────────────────────┘   │
├──────────┴──────────────────────────────────────────────────┤
│ AiDock (market insights, strategic recommendations)         │
└─────────────────────────────────────────────────────────────┘
```

## Component Tree

```
MarketIntelligencePage
├── ExecutiveHeader
├── Breadcrumb
├── MarketIntelligenceHeader
│   ├── CalendarRange (date range)
│   ├── ChipSelect (agencies)
│   ├── ChipSelect (zones)
│   └── Button (Export Report)
├── MarketIntelligence
│   ├── Tabs
│   │   ├── TrendsTab
│   │   │   └── TrendAnalysis
│   │   │       ├── Chart (price trends)
│   │   │       ├── Chart (volume trends)
│   │   │       └── AiInsight × N
│   │   ├── CompetitorsTab
│   │   │   └── CompetitorLandscape
│   │   │       ├── CompetitorMatrix
│   │   │       ├── CompetitorCard × N
│   │   │       └── ThreatAnalysis
│   │   ├── AgenciesTab
│   │   │   └── AgencyAnalytics
│   │   │       ├── AgencyRanking
│   │   │       ├── AgencyCard × N
│   │   │       └── PerformanceChart
│   │   ├── ZonesTab
│   │   │   └── ZoneIntelligence
│   │   │       ├── ZoneHeatmap
│   │   │       ├── ZoneCard × N
│   │   │       └── GeographicAnalysis
│   │   └── InsightsTab
│   │       └── AiInsights
│   │           ├── InsightCard × N
│   │           │   ├── type
│   │           │   ├── title
│   │           │   ├── description
│   │           │   └── ConfidenceBadge
│   │           └── RecommendationList
│   └── MarketSummary
│       ├── KpiCard (total_market_size)
│       ├── KpiCard (growth_rate)
│       ├── KpiCard (competition_level)
│       └── KpiCard (opportunity_score)
└── AiDock
    ├── AgentCard (Intelligence Agent)
    └── EvidencePanel (market insights)
```

## Data Sources

### Market Trends
```typescript
// API: GET /api/v1/knowledge/market/trends
interface MarketTrends {
  price_trends: TrendData[];
  volume_trends: TrendData[];
  forecasts: ForecastData[];
}

interface TrendData {
  period: string;
  value: number;
  change_pct: number;
  trend: 'rising' | 'stable' | 'falling';
}

interface ForecastData {
  period: string;
  predicted: number;
  confidence: number;
  range: { min: number; max: number };
}
```

### Competitor Landscape
```typescript
// API: GET /api/v1/knowledge/market/competitors
interface CompetitorLandscape {
  competitors: CompetitorProfile[];
  market_concentration: number;
  threat_level: string;
}

interface CompetitorProfile {
  competitor_id: string;
  name: string;
  win_rate: number;
  avg_bid_ratio: number;
  specializations: string[];
  zones: string[];
  threat_score: number;
}
```

### AI Insights
```typescript
// API: GET /api/v1/knowledge/market/insights
interface AiInsightList {
  insights: AiInsight[];
  recommendations: Recommendation[];
}

interface AiInsight {
  insight_id: string;
  type: 'trend' | 'opportunity' | 'threat' | 'recommendation';
  title: string;
  description: string;
  confidence: number;
  evidence: string;
  impact: 'high' | 'medium' | 'low';
}
```

### React Query
```typescript
const { data: trends } = useQuery({
  queryKey: ['knowledge', 'market', 'trends', dateRange],
  queryFn: () => api.get('/api/v1/knowledge/market/trends', { params: dateRange }),
});

const { data: competitors } = useQuery({
  queryKey: ['knowledge', 'market', 'competitors'],
  queryFn: () => api.get('/api/v1/knowledge/market/competitors'),
});

const { data: insights } = useQuery({
  queryKey: ['knowledge', 'market', 'insights'],
  queryFn: () => api.get('/api/v1/knowledge/market/insights'),
});
```

## Zustand Store
```typescript
// stores/marketIntelligenceStore.ts
interface MarketIntelligenceState {
  activeTab: string;
  dateRange: { start: string; end: string };
  setTab: (tab: string) => void;
  setDateRange: (range: { start: string; end: string }) => void;
}
```

## Interactions

### View Trends
1. Click Trends tab
2. Analyze price/volume charts
3. View forecasts
4. Read AI insights

### Analyze Competitors
1. Click Competitors tab
2. View competitor matrix
3. Analyze threat levels
4. Read strategic insights

### Explore Zones
1. Click Zones tab
2. View zone heatmap
3. Analyze geographic patterns
4. Identify opportunities

### Read Insights
1. Click Insights tab
2. View AI recommendations
3. Read evidence
4. Take action

## Responsive Breakpoints

| Breakpoint | Layout |
|------------|--------|
| Desktop (>1024px) | Full tabs with charts |
| Tablet (768-1024px) | Stacked tabs |
| Mobile (<768px) | Single tab view |

## Loading States
- Charts: Skeleton with shimmer
- Competitors: Skeleton cards
- Insights: Skeleton cards

## Error States
- No data: EmptyState
- API error: Toast notification
- Partial data: Show available

## Accessibility
- Tab navigation with arrow keys
- Charts have table fallback
- Screen reader: "Trend: rising 5%"
- Keyboard: Tab through elements

## Telemetry
- `market_intelligence.view` — Screen loaded
- `market_intelligence.tab_switch` — Tab changed
- `market_intelligence.export` — Report exported

## Implementation Notes
- 5 tabs with deep analysis
- Charts for visualization
- AI-powered insights
- AiDock provides market intelligence
- Export for strategic planning
