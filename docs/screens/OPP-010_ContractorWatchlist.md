# OPP-010: Contractor Watchlist Screen Specification

**Module:** `features/contractor-watchlist/ContractorWatchlistPage`
**Layer:** features
**Version:** 1.0.0
**Status:** Draft
**Workspace:** Opportunity

## Purpose
Track and monitor specific contractors and their activities.

## Screen Layout

```
┌─────────────────────────────────────────────────────────────┐
│ ExecutiveHeader                                             │
├──────────┬──────────────────────────────────────────────────┤
│          │ Breadcrumb: Opportunity > Contractor Watchlist    │
│ Workspace├──────────────────────────────────────────────────┤
│   Nav    │ ContractorWatchlistHeader (count, alerts)        │
│          ├──────────────────────────────────────────────────┤
│          │ ContractorWatchlist (main content)               │
│          │ ┌────────────────────────────────────────────┐   │
│          │ │ SearchBar (contractor search)               │   │
│          │ ├────────────────────────────────────────────┤   │
│          │ │ WatchlistGrid (watched contractors)         │   │
│          │ │ ┌──────┬──────┬──────┬──────┐              │   │
│          │ │ │Contr.│Contr.│Contr.│Contr.│              │   │
│          │ │ │  A   │  B   │  C   │  D   │              │   │
│          │ │ └──────┴──────┴──────┴──────┘              │   │
│          │ ├────────────────────────────────────────────┤   │
│          │ │ ActivityFeed (recent activities)            │   │
│          │ └────────────────────────────────────────────┘   │
├──────────┴──────────────────────────────────────────────────┤
│ AiDock (contractor insights)                                │
└─────────────────────────────────────────────────────────────┘
```

## Component Tree

```
ContractorWatchlistPage
├── ExecutiveHeader
├── Breadcrumb
├── ContractorWatchlistHeader
│   ├── KpiStrip (watched_count, alert_count)
│   └── Button (Add Contractor)
├── ContractorWatchlist
│   ├── SearchPanel
│   │   ├── SearchBar
│   │   └── SearchResults
│   │       └── ContractorResult × N
│   │           ├── name
│   │           ├── rating
│   │           └── Button (Add to Watchlist)
│   ├── WatchlistGrid
│   │   └── ContractorCard × N
│   │       ├── name
│   │       ├── status
│   │       ├── last_activity
│   │       ├── alerts
│   │       └── Button (View Details)
│   ├── ActivityFeed
│   │   └── ActivityItem × N
│   │       ├── contractor
│   │       ├── activity
│   │       └── timestamp
│   └── AlertPanel
│       └── Alert × N
│           ├── type
│           ├── message
│           └── Button (Dismiss)
└── AiDock
    ├── AgentCard (Competitor Agent)
    └── EvidencePanel (contractor insights)
```

## Data Sources

### Contractor Watchlist
```typescript
// API: GET /api/v1/opportunities/watchlist
interface WatchlistData {
  contractors: WatchedContractor[];
  total_count: number;
  alert_count: number;
}

interface WatchedContractor {
  contractor_id: string;
  name: string;
  status: 'active' | 'inactive' | 'flagged';
  rating: number;
  last_activity: string;
  alerts: Alert[];
  added_at: string;
}

interface Alert {
  alert_id: string;
  type: string;
  message: string;
  severity: 'info' | 'warning' | 'critical';
  created_at: string;
}
```

### React Query
```typescript
const { data: watchlist } = useQuery({
  queryKey: ['opportunities', 'watchlist'],
  queryFn: () => api.get('/api/v1/opportunities/watchlist'),
});

const addToWatchlist = useMutation({
  mutationFn: (contractorId: string) => api.post('/api/v1/opportunities/watchlist', { contractor_id: contractorId }),
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ['opportunities', 'watchlist'] });
    toast.success('Added to watchlist');
  },
});

const removeFromWatchlist = useMutation({
  mutationFn: (contractorId: string) => api.delete(`/api/v1/opportunities/watchlist/${contractorId}`),
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ['opportunities', 'watchlist'] });
    toast.success('Removed from watchlist');
  },
});
```

## Zustand Store
```typescript
// stores/contractorWatchlistStore.ts
interface ContractorWatchlistState {
  searchQuery: string;
  selectedContractor: string | null;
  setSearch: (query: string) => void;
  setContractor: (id: string | null) => void;
}
```

## Interactions

### Add Contractor
1. Search contractor
2. Select from results
3. Add to watchlist
4. Update grid

### View Details
1. Click contractor card
2. View profile
3. See activities
4. Review alerts

### Dismiss Alert
1. Click alert
2. View details
3. Dismiss alert
4. Update count

### Remove from Watchlist
1. Click Remove button
2. Confirm removal
3. Update grid
4. Refresh count

## Responsive Breakpoints

| Breakpoint | Layout |
|------------|--------|
| Desktop (>1024px) | Full grid + feed |
| Tablet (768-1024px) | Stacked layout |
| Mobile (<768px) | Simplified list |

## Loading States
- Watchlist: Skeleton grid
- Activity: Skeleton feed
- Search: Loading spinner

## Error States
- Add failure: Toast error
- Remove failure: Toast error
- Network error: Toast notification

## Accessibility
- Contractors are focusable
- Alerts announced via `aria-live`
- Screen reader: "Contractor X, status: active"
- Keyboard: Tab through contractors

## Telemetry
- `contractor_watchlist.view` — Screen loaded
- `contractor_watchlist.add` — Contractor added
- `contractor_watchlist.remove` — Contractor removed
- `contractor_watchlist.alert_dismiss` — Alert dismissed

## Implementation Notes
- Real-time contractor monitoring
- Activity feed
- Alert system
- AiDock provides contractor insights
- Export for analysis
