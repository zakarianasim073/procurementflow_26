# KNOW-001: Market Research Screen Specification

**Module:** `features/knowledge/MarketResearchPage`
**Layer:** features
**Version:** 1.0.0
**Status:** Draft
**Workspace:** Knowledge

## Purpose
Market intelligence hub for rate trends, agency analytics, zone comparisons, and competitive landscape analysis.

## Screen Layout

```
┌─────────────────────────────────────────────────────────────┐
│ ExecutiveHeader                                             │
├──────────┬──────────────────────────────────────────────────┤
│          │ Breadcrumb: Knowledge > Market Research           │
│ Workspace├──────────────────────────────────────────────────┤
│   Nav    │ MarketResearchHeader (date range, filters)       │
│          ├──────────────────────────────────────────────────┤
│          │ MarketInsights (main content)                    │
│          │ ┌────────────────────────────────────────────┐   │
│          │ │ Tabs: [Trends] [Agencies] [Zones] [Rates]  │   │
│          │ ├────────────────────────────────────────────┤   │
│          │ │ TrendAnalysis (line charts, sparklines)    │   │
│          │ │ AgencyPerformance (bar charts, rankings)   │   │
│          │ │ ZoneComparison (heatmap, geographic)       │   │
│          │ │ RateAnalysis (table, SOR trends)           │   │
│          │ └────────────────────────────────────────────┘   │
├──────────┴──────────────────────────────────────────────────┤
│ AiDock (market insights, trend predictions)                 │
└─────────────────────────────────────────────────────────────┘
```

## Component Tree

```
MarketResearchPage
├── ExecutiveHeader
├── Breadcrumb
├── MarketResearchHeader
│   ├── CalendarRange (date range)
│   ├── ChipSelect (agencies)
│   ├── ChipSelect (zones)
│   └── Button (Export Report)
├── MarketInsights
│   ├── Tabs
│   │   ├── TrendsTab
│   │   │   ├── Chart (line - price trends)
│   │   │   ├── Sparkline (item trends)
│   │   │   └── TrendAnalysis (summary)
│   │   ├── AgenciesTab
│   │   │   ├── Chart (bar - agency performance)
│   │   │   ├── Table (agency rankings)
│   │   │   └── Badge (top performer)
│   │   ├── ZonesTab
│   │   │   ├── Heatmap (zone activity)
│   │   │   ├── Chart (zone comparison)
│   │   │   └── ZoneStatistics (summary)
│   │   └── RatesTab
│   │       ├── RateAnalysisTable (SOR trends)
│   │       ├── Chart (rate changes)
│   │       └── EvidencePanel (rate sources)
│   └── MarketSummary
│       ├── KpiCard (total_tenders)
│       ├── KpiCard (avg_value)
│       ├── KpiCard (competition_level)
│       └── KpiCard (market_trend)
└── AiDock
    ├── AgentCard (Intelligence Agent)
    └── EvidencePanel (market insights)
```

## Data Sources

### Market Trends
```typescript
// API: GET /api/v1/knowledge/market/trends
interface MarketTrends {
  period: string;
  items: TrendItem[];
  overall_trend: 'rising' | 'stable' | 'falling';
  confidence: number;
}

interface TrendItem {
  item_code: string;
  description: string;
  current_rate: number;
  previous_rate: number;
  change_pct: number;
  trend: 'rising' | 'stable' | 'falling';
  data_points: { date: string; value: number }[];
}
```

### Agency Performance
```typescript
// API: GET /api/v1/knowledge/market/agencies
interface AgencyPerformance {
  agencies: AgencyMetric[];
  rankings: AgencyRanking[];
}

interface AgencyMetric {
  agency: string;
  total_tenders: number;
  awarded_count: number;
  avg_value: number;
  win_rate: number;
  zones: string[];
}

interface AgencyRanking {
  agency: string;
  rank: number;
  metric: string;
  value: number;
}
```

### Zone Comparison
```typescript
// API: GET /api/v1/knowledge/market/zones
interface ZoneComparison {
  zones: ZoneMetric[];
  heatmap: HeatmapData[];
}

interface ZoneMetric {
  zone: string;
  division: string;
  tender_count: number;
  total_value: number;
  avg_competition: number;
  top_agencies: string[];
}

interface HeatmapData {
  zone: string;
  division: string;
  value: number;
  intensity: number;
}
```

### React Query
```typescript
const { data: trends } = useQuery({
  queryKey: ['knowledge', 'market', 'trends', dateRange],
  queryFn: () => api.get('/api/v1/knowledge/market/trends', { params: dateRange }),
});

const { data: agencies } = useQuery({
  queryKey: ['knowledge', 'market', 'agencies'],
  queryFn: () => api.get('/api/v1/knowledge/market/agencies'),
});

const { data: zones } = useQuery({
  queryKey: ['knowledge', 'market', 'zones'],
  queryFn: () => api.get('/api/v1/knowledge/market/zones'),
});
```

## Zustand Store
```typescript
// stores/marketResearchStore.ts
interface MarketResearchState {
  dateRange: { start: string; end: string };
  selectedAgencies: string[];
  selectedZones: string[];
  activeTab: 'trends' | 'agencies' | 'zones' | 'rates';
  setDateRange: (range: { start: string; end: string }) => void;
  setAgencies: (agencies: string[]) => void;
  setZones: (zones: string[]) => void;
  setTab: (tab: string) => void;
}
```

## Interactions

### Tab Switching
1. Click tab header
2. Update URL: `/market-research?tab=trends`
3. Preserve filter state
4. Lazy load tab content

### Trend Analysis
1. Select item from list
2. View historical chart
3. Compare across agencies
4. Export trend report

### Agency Comparison
1. Select multiple agencies
2. Side-by-side comparison
3. View win patterns
4. Analyze specializations

### Zone Analysis
1. Click heatmap cell
2. View zone details
3. Compare zones
4. Export zone report

## Responsive Breakpoints

| Breakpoint | Layout |
|------------|--------|
| Desktop (>1024px) | Full tabs with charts |
| Tablet (768-1024px) | Scrollable tabs |
| Mobile (<768px) | Bottom tab bar |

## Loading States
- Charts: Skeleton with shimmer
- Tables: Skeleton rows
- Heatmap: Loading grid

## Error States
- No data: EmptyState
- API error: Toast notification
- Partial data: Show available

## Accessibility
- Tab navigation with arrow keys
- Chart data available as table
- Screen reader: "Trend: rising 5%"
- Keyboard: Enter to select items

## Telemetry
- `market_research.view` — Screen loaded
- `market_research.tab_switch` — Tab changed
- `market_research.export` — Report exported

## Implementation Notes
- 4 tabs with lazy loading
- Charts use Chart component
- Heatmap for zone visualization
- AiDock provides market insights
- Export generates market report
