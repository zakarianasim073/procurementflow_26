# OPP-014: Watchlist Screen Specification

**Module:** `features/watchlist/WatchlistPage`
**Layer:** features
**Version:** 1.0.0
**Status:** Draft
**Workspace:** Opportunity

## Purpose
Track watched tenders, contractors, and opportunities.

## Screen Layout

```
┌─────────────────────────────────────────────────────────────┐
│ ExecutiveHeader                                             │
├──────────┬──────────────────────────────────────────────────┤
│          │ Breadcrumb: Opportunity > Watchlist               │
│ Workspace├──────────────────────────────────────────────────┤
│   Nav    │ WatchlistHeader (count, alerts)                  │
│          ├──────────────────────────────────────────────────┤
│          │ Watchlist (main content)                         │
│          │ ┌────────────────────────────────────────────┐   │
│          │ │ Tabs: [Tenders] [Contractors] [Alerts]      │   │
│          │ ├────────────────────────────────────────────┤   │
│          │ │ TendersTab (watched tenders)                │   │
│          │ │ ContractorsTab (watched contractors)        │   │
│          │ │ AlertsTab (watchlist alerts)                │   │
│          │ └────────────────────────────────────────────┘   │
├──────────┴──────────────────────────────────────────────────┤
│ AiDock (watchlist insights)                                 │
└─────────────────────────────────────────────────────────────┘
```

## Component Tree

```
WatchlistPage
├── ExecutiveHeader
├── Breadcrumb
├── WatchlistHeader
│   ├── KpiStrip (watched_count, alert_count)
│   └── Button (Add to Watchlist)
├── Watchlist
│   ├── Tabs
│   │   ├── TendersTab
│   │   │   └── TenderList
│   │   │       └── TenderCard × N
│   │   │           ├── name
│   │   │           ├── agency
│   │   │           ├── value
│   │   │           ├── deadline
│   │   │           └── actions (view, remove)
│   │   ├── ContractorsTab
│   │   │   └── ContractorList
│   │   │       └── ContractorCard × N
│   │   │           ├── name
│   │   │           ├── rating
│   │   │           ├── recent_activity
│   │   │           └── actions (view, remove)
│   │   └── AlertsTab
│   │       └── AlertList
│   │           └── AlertCard × N
│   │               ├── type
│   │               ├── message
│   │               ├── severity
│   │               └── actions (view, dismiss)
│   └── WatchlistStats
│       ├── chart (activity_trend)
│       └── chart (alert_distribution)
└── AiDock
    ├── AgentCard (Watchlist Agent)
    └── EvidencePanel (watchlist insights)
```

## Data Sources

### Watchlist
```typescript
// API: GET /api/v1/opportunities/watchlist
interface WatchlistData {
  tenders: WatchedTender[];
  contractors: WatchedContractor[];
  alerts: WatchlistAlert[];
  total_count: number;
  alert_count: number;
}

interface WatchedTender {
  tender_id: string;
  name: string;
  agency: string;
  value: number;
  deadline: string;
  status: string;
  added_at: string;
}

interface WatchedContractor {
  contractor_id: string;
  name: string;
  rating: number;
  recent_activity: string;
  added_at: string;
}

interface WatchlistAlert {
  alert_id: string;
  type: string;
  message: string;
  severity: 'info' | 'warning' | 'critical';
  created_at: string;
  read: boolean;
}
```

### React Query
```typescript
const { data: watchlist } = useQuery({
  queryKey: ['opportunities', 'watchlist'],
  queryFn: () => api.get('/api/v1/opportunities/watchlist'),
});

const removeFromWatchlist = useMutation({
  mutationFn: ({ type, id }: { type: string; id: string }) =>
    api.delete(`/api/v1/opportunities/watchlist/${type}/${id}`),
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ['opportunities', 'watchlist'] });
    toast.success('Removed from watchlist');
  },
});
```

## Zustand Store
```typescript
// stores/watchlistStore.ts
interface WatchlistState {
  activeTab: string;
  setTab: (tab: string) => void;
}
```

## Interactions

### View Tenders
1. Click Tenders tab
2. View tender list
3. Check details
4. Remove if needed

### View Contractors
1. Click Contractors tab
2. View contractor list
3. Check activity
4. Remove if needed

### View Alerts
1. Click Alerts tab
2. View alert list
3. Check severity
4. Dismiss if needed

### Add to Watchlist
1. Click Add button
2. Select type
3. Choose item
4. Confirm addition

## Responsive Breakpoints

| Breakpoint | Layout |
|------------|--------|
| Desktop (>1024px) | Full tabs + list |
| Tablet (768-1024px) | Stacked tabs |
| Mobile (<768px) | Simplified list |

## Loading States
- Watchlist: Skeleton cards
- Alerts: Loading list
- Stats: Loading charts

## Error States
- Remove failure: Toast error
- Load failure: Retry button
- Network error: Toast notification

## Accessibility
- Items are focusable
- Count announced via `aria-live`
- Screen reader: "Tender: BWDB Road Project, watched"
- Keyboard: Tab through items

## Telemetry
- `watchlist.view` — Screen loaded
- `watchlist.add` — Item added
- `watchlist.remove` — Item removed
- `watchlist.alert_dismiss` — Alert dismissed

## Implementation Notes
- Multi-type watchlist
- Alert system
- Activity tracking
- AiDock provides watchlist insights
- Export for analysis
