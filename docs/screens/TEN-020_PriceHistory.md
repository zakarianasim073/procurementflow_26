# TEN-020: Price History Screen Specification

**Module:** `features/price-history/PriceHistoryPage`
**Layer:** features
**Version:** 1.0.0
**Status:** Draft
**Workspace:** Acquisition

## Purpose
Track and analyze historical pricing trends for SOR items and materials.

## Screen Layout

```
┌─────────────────────────────────────────────────────────────┐
│ ExecutiveHeader                                             │
├──────────┬──────────────────────────────────────────────────┤
│          │ Breadcrumb: Acquisition > Price History           │
│ Workspace├──────────────────────────────────────────────────┤
│   Nav    │ PriceHistoryHeader (item, date range)            │
│          ├──────────────────────────────────────────────────┤
│          │ PriceHistory (main content)                      │
│          │ ┌────────────────────────────────────────────┐   │
│          │ │ PriceChart (historical trend)               │   │
│          │ │ ┌──────────────────────────────────────────┐│   │
│          │ │ │    Price                                ││   │
│          │ │ │      ╱╲                                ││   │
│          │ │ │     ╱  ╲                               ││   │
│          │ │ │    ╱    ╲                              ││   │
│          │ │ │   ╱      ╲                             ││   │
│          │ │ │ ──────────────────── Time               ││   │
│          │ │ └──────────────────────────────────────────┘│   │
│          │ ├────────────────────────────────────────────┤   │
│          │ │ PriceTable (detailed data)                  │   │
│          │ └────────────────────────────────────────────┘   │
├──────────┴──────────────────────────────────────────────────┤
│ AiDock (price insights, forecasts)                          │
└─────────────────────────────────────────────────────────────┘
```

## Component Tree

```
PriceHistoryPage
├── ExecutiveHeader
├── Breadcrumb
├── PriceHistoryHeader
│   ├── SearchBar (item search)
│   ├── CalendarRange (date range)
│   ├── ChipSelect (agencies)
│   └── Button (Export)
├── PriceHistory
│   ├── PriceChart
│   │   ├── LineChart (price_trend)
│   │   ├── BarChart (volume)
│   │   └── Annotation × N
│   │       ├── date
│   │       ├── event
│   │       └── impact
│   ├── PriceTable
│   │   └── Table<PriceEntry>
│   │       ├── date
│   │       ├── agency
│   │       ├── rate
│   │       ├── change
│   │       └── percentage
│   ├── PriceAnalysis
│   │   ├── volatility
│   │   ├── trend
│   │   └── forecast
│   └── RelatedItems
│       └── ItemCard × N
│           ├── code
│           ├── description
│           └── current_rate
└── AiDock
    ├── AgentCard (Pricing Agent)
    └── EvidencePanel (price insights)
```

## Data Sources

### Price History
```typescript
// API: GET /api/v1/sor/history
interface PriceHistory {
  item_code: string;
  description: string;
  entries: PriceEntry[];
  analysis: PriceAnalysis;
}

interface PriceEntry {
  date: string;
  agency: string;
  zone: string;
  rate: number;
  change: number;
  change_percentage: number;
}

interface PriceAnalysis {
  volatility: number;
  trend: 'increasing' | 'decreasing' | 'stable';
  forecast: { date: string; predicted_rate: number }[];
}
```

### React Query
```typescript
const { data: history } = useQuery({
  queryKey: ['sor', 'history', itemCode, filters],
  queryFn: () => api.get('/api/v1/sor/history', { params: { item_code: itemCode, ...filters } }),
  enabled: !!itemCode,
});
```

## Zustand Store
```typescript
// stores/priceHistoryStore.ts
interface PriceHistoryState {
  selectedItem: string | null;
  dateRange: { start: string; end: string } | null;
  selectedAgencies: string[];
  setItem: (code: string | null) => void;
  setDateRange: (range: { start: string; end: string } | null) => void;
  setAgencies: (agencies: string[]) => void;
}
```

## Interactions

### Select Item
1. Search item
2. Select from results
3. Load history
4. Display chart

### Change Date Range
1. Open calendar
2. Select range
3. Update chart
4. Refresh table

### View Analysis
1. View trend
2. Check volatility
3. Read forecast
4. Get insights

### Export History
1. Click Export
2. Choose format
3. Include analysis
4. Download file

## Responsive Breakpoints

| Breakpoint | Layout |
|------------|--------|
| Desktop (>1024px) | Full chart + table |
| Tablet (768-1024px) | Chart with table below |
| Mobile (<768px) | Simplified chart |

## Loading States
- Chart: Loading animation
- Table: Skeleton rows
- Analysis: Loading spinner

## Error States
- Load failure: Retry button
- No data: EmptyState
- Network error: Toast notification

## Accessibility
- Chart is keyboard navigable
- Data points announced via `aria-live`
- Screen reader: "Rate: 100 on Jan 1, 2026"
- Keyboard: Arrow keys to navigate points

## Telemetry
- `price_history.view` — Screen loaded
- `price_history.item_select` — Item selected
- `price_history.date_change` — Date range changed
- `price_history.export` — History exported

## Implementation Notes
- Interactive price charts
- Historical trend analysis
- Price forecasting
- AiDock provides price insights
- Export for analysis
