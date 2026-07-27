# OPP-007: Contractor Directory Screen Specification

**Module:** `features/contractor/ContractorDirectoryPage`
**Layer:** features
**Version:** 1.0.0
**Status:** Draft
**Workspace:** Discovery

## Purpose
Contractor database, performance tracking, and partnership management.

## Screen Layout

```
┌─────────────────────────────────────────────────────────────┐
│ ExecutiveHeader                                             │
├──────────┬──────────────────────────────────────────────────┤
│          │ Breadcrumb: Discovery > Contractor Directory      │
│ Workspace├──────────────────────────────────────────────────┤
│   Nav    │ ContractorDirectoryHeader (count, filters)       │
│          ├──────────────────────────────────────────────────┤
│          │ ContractorDirectory (main content)               │
│          │ ┌────────────────────────────────────────────┐   │
│          │ │ SearchBar (contractor search)               │   │
│          │ ├────────────────────────────────────────────┤   │
│          │ │ FilterPanel (type, zone, specialization)    │   │
│          │ ├────────────────────────────────────────────┤   │
│          │ │ ContractorList (cards grid)                 │   │
│          │ │ ┌──────────────┐ ┌──────────────┐          │   │
│          │ │ │ Contractor 1 │ │ Contractor 2 │          │   │
│          │ │ │ Win Rate: 45%│ │ Win Rate: 32%│          │   │
│          │ │ │ Specialization│ │ Specialization│         │   │
│          │ │ └──────────────┘ └──────────────┘          │   │
│          │ └────────────────────────────────────────────┘   │
├──────────┴──────────────────────────────────────────────────┤
│ AiDock (contractor insights, partnership suggestions)       │
└─────────────────────────────────────────────────────────────┘
```

## Component Tree

```
ContractorDirectoryPage
├── ExecutiveHeader
├── Breadcrumb
├── ContractorDirectoryHeader
│   ├── KpiStrip (contractor_count, active_count, avg_win_rate)
│   └── Button (Add Contractor)
├── ContractorDirectory
│   ├── SearchBar (keyword search)
│   ├── FilterPanel
│   │   ├── ChipSelect (type: government/private)
│   │   ├── ChipSelect (zones)
│   │   ├── ChipSelect (specializations)
│   │   └── RangeSlider (win_rate)
│   ├── ContractorList
│   │   └── ContractorCard × N
│   │       ├── Avatar (company logo)
│   │       ├── name
│   │       ├── type
│   │       ├── zones
│   │       ├── specializations
│   │       ├── win_rate
│   │       └── Button (View Profile)
│   └── ContractorDetail
│       ├── company_info
│       ├── performance_metrics
│       ├── bid_history
│       └── partnerships
└── AiDock
    ├── AgentCard (Competitor Agent)
    └── EvidencePanel (contractor insights)
```

## Data Sources

### Contractors
```typescript
// API: GET /api/v1/competitors/contractors
interface ContractorList {
  contractors: Contractor[];
  total_count: number;
}

interface Contractor {
  contractor_id: string;
  name: string;
  type: 'government' | 'private';
  zones: string[];
  specializations: string[];
  win_rate: number;
  total_bids: number;
  total_wins: number;
  avg_bid_value: number;
  last_active: string;
}
```

### React Query
```typescript
const { data: contractors } = useQuery({
  queryKey: ['competitors', 'contractors', filters],
  queryFn: () => api.get('/api/v1/competitors/contractors', { params: filters }),
});

const addContractor = useMutation({
  mutationFn: (request: AddContractorRequest) => api.post('/api/v1/competitors/contractors', request),
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ['competitors', 'contractors'] });
    toast.success('Contractor added');
  },
});
```

## Zustand Store
```typescript
// stores/contractorDirectoryStore.ts
interface ContractorDirectoryState {
  filters: {
    type: string[];
    zones: string[];
    specializations: string[];
    minWinRate: number;
  };
  setFilter: <K extends keyof ContractorDirectoryState['filters']>(key: K, value: ContractorDirectoryState['filters'][K]) => void;
}
```

## Interactions

### Search Contractors
1. Type in search bar
2. Debounce 300ms
3. Filter results
4. Update list

### Filter Contractors
1. Apply filter
2. Refetch contractors
3. Update list
4. Preserve search

### View Profile
1. Click contractor card
2. Open ContractorDetail
3. View performance
4. Analyze history

### Add Contractor
1. Click "Add Contractor"
2. Fill form
3. Submit
4. Update list

## Responsive Breakpoints

| Breakpoint | Layout |
|------------|--------|
| Desktop (>1024px) | Grid cards with filters |
| Tablet (768-1024px) | Stacked cards |
| Mobile (<768px) | List view, swipe details |

## Loading States
- Contractors: Skeleton cards
- Detail: Skeleton content
- Search: Loading spinner

## Error States
- Load failure: Retry button
- Add failure: Toast error
- Network error: Toast notification

## Accessibility
- Cards are focusable
- Count announced via `aria-live`
- Screen reader: "Contractor X, win rate 45%"
- Keyboard: Enter to view, Tab to navigate

## Telemetry
- `contractor_directory.view` — Screen loaded
- `contractor_directory.search` — Search performed
- `contractor_directory.filter` — Filter applied
- `contractor_directory.add` — Contractor added

## Implementation Notes
- Searchable contractor database
- Filterable by type/zone/specialization
- Contractor profiles with metrics
- AiDock provides contractor insights
- Export for partnership analysis
