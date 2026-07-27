# TEN-019: SOR Comparison Screen Specification

**Module:** `features/sor-comparison/SorComparisonPage`
**Layer:** features
**Version:** 1.0.0
**Status:** Draft
**Workspace:** Acquisition

## Purpose
Compare SOR rates across agencies, zones, and time periods.

## Screen Layout

```
┌─────────────────────────────────────────────────────────────┐
│ ExecutiveHeader                                             │
├──────────┬──────────────────────────────────────────────────┤
│          │ Breadcrumb: Acquisition > SOR Comparison          │
│ Workspace├──────────────────────────────────────────────────┤
│   Nav    │ SorComparisonHeader (agencies, zones)            │
│          ├──────────────────────────────────────────────────┤
│          │ SorComparison (main content)                     │
│          │ ┌────────────────────────────────────────────┐   │
│          │ │ ComparisonTable (side-by-side)              │   │
│          │ │ ┌──────────┬──────────┬──────────┐          │   │
│          │ │ │ BWDB     │ PWD      │ LGED     │          │   │
│          │ │ │ Zone A   │ Zone A   │ Zone A   │          │   │
│          │ │ │ 100      │ 110      │ 95       │          │   │
│          │ │ └──────────┴──────────┴──────────┘          │   │
│          │ ├────────────────────────────────────────────┤   │
│          │ │ VarianceAnalysis (differences)              │   │
│          │ └────────────────────────────────────────────┘   │
├──────────┴──────────────────────────────────────────────────┤
│ AiDock (SOR insights, optimization)                         │
└─────────────────────────────────────────────────────────────┘
```

## Component Tree

```
SorComparisonPage
├── ExecutiveHeader
├── Breadcrumb
├── SorComparisonHeader
│   ├── ChipSelect (agencies: BWDB, PWD, LGED)
│   ├── ChipSelect (zones: A, B, C, D)
│   └── Button (Export Comparison)
├── SorComparison
│   ├── ComparisonTable
│   │   └── Table<SorComparison>
│   │       ├── code
│   │       ├── description
│   │       ├── bwdb_rate
│   │       ├── pwd_rate
│   │       ├── lged_rate
│   │       └── variance
│   ├── VarianceAnalysis
│   │   ├── Chart (variance_distribution)
│   │   ├── Table<VarianceItem>
│   │   │   ├── agency
│   │   │   ├── avg_variance
│   │   │   └── count
│   │   └── AiInsight × N
│   └── ZoneMapping
│       ├── ZoneTable
│       │   └── ZoneRow × N
│       │       ├── division
│       │       ├── bwdb_zone
│       │       ├── pwd_zone
│       │       └── lged_zone
│       └── ZoneChart
└── AiDock
    ├── AgentCard (SOR Agent)
    └── EvidencePanel (SOR insights)
```

## Data Sources

### SOR Comparison
```typescript
// API: GET /api/v1/sor/compare
interface SorComparison {
  items: SorItem[];
  agencies: string[];
  zones: string[];
}

interface SorItem {
  code: string;
  description: string;
  unit: string;
  rates: Record<string, number>; // agency_zone -> rate
  variance: number;
}
```

### React Query
```typescript
const { data: comparison } = useQuery({
  queryKey: ['sor', 'compare', filters],
  queryFn: () => api.get('/api/v1/sor/compare', { params: filters }),
});
```

## Zustand Store
```typescript
// stores/sorComparisonStore.ts
interface SorComparisonState {
  selectedAgencies: string[];
  selectedZones: string[];
  setAgencies: (agencies: string[]) => void;
  setZones: (zones: string[]) => void;
}
```

## Interactions

### Select Agencies
1. Toggle agency chip
2. Update comparison
3. Refresh table
4. Recalculate variance

### Select Zones
1. Toggle zone chip
2. Update rates
3. Refresh table
4. Show variance

### View Variance
1. Click variance cell
2. View details
3. Analyze differences
4. Read insights

### Export Comparison
1. Click Export button
2. Choose format
3. Include all rates
4. Download file

## Responsive Breakpoints

| Breakpoint | Layout |
|------------|--------|
| Desktop (>1024px) | Full comparison table |
| Tablet (768-1024px) | Horizontal scroll |
| Mobile (<768px) | Stacked cards |

## Loading States
- Table: Skeleton rows
- Variance: Skeleton chart
- Mapping: Skeleton table

## Error States
- Load failure: Retry button
- No data: EmptyState
- Network error: Toast notification

## Accessibility
- Table cells are focusable
- Variances highlighted via `aria-live`
- Screen reader: "BWDB: 100, PWD: 110, variance: 10%"
- Keyboard: Arrow keys to navigate

## Telemetry
- `sor_comparison.view` — Screen loaded
- `sor_comparison.agency_toggle` — Agency toggled
- `sor_comparison.zone_toggle` — Zone toggled
- `sor_comparison.export` — Comparison exported

## Implementation Notes
- Side-by-side rate comparison
- Variance analysis
- Zone mapping visualization
- AiDock provides SOR insights
- Export for analysis
