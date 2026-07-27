# OPP-008: Tender Watchlist Screen Specification

**Module:** `features/watchlist/WatchlistPage`
**Layer:** features
**Version:** 1.0.0
**Status:** Draft
**Workspace:** Discovery

## Purpose
Monitor followed tenders, track changes, and receive notifications.

## Screen Layout

```
┌─────────────────────────────────────────────────────────────┐
│ ExecutiveHeader                                             │
├──────────┬──────────────────────────────────────────────────┤
│          │ Breadcrumb: Discovery > Tender Watchlist          │
│ Workspace├──────────────────────────────────────────────────┤
│   Nav    │ WatchlistHeader (count, filters)                 │
│          ├──────────────────────────────────────────────────┤
│          │ Watchlist (main content)                         │
│          │ ┌────────────────────────────────────────────┐   │
│          │ │ FilterBar (status, agency, deadline)        │   │
│          │ ├────────────────────────────────────────────┤   │
│          │ │ WatchlistGrid (tender cards)                │   │
│          │ │ ┌──────────────┐ ┌──────────────┐          │   │
│          │ │ │ Tender 1     │ │ Tender 2     │          │   │
│          │ │ │ Deadline: 5d │ │ Deadline: 12d│          │   │
│          │ │ │ Changes: 2   │ │ Changes: 0   │          │   │
│          │ │ └──────────────┘ └──────────────┘          │   │
│          │ └────────────────────────────────────────────┘   │
├──────────┴──────────────────────────────────────────────────┤
│ AiDock (watchlist insights, recommendations)                │
└─────────────────────────────────────────────────────────────┘
```

## Component Tree

```
WatchlistPage
├── ExecutiveHeader
├── Breadcrumb
├── WatchlistHeader
│   ├── KpiStrip (watch_count, deadline_soon, changes)
│   └── Button (Add Tender)
├── Watchlist
│   ├── FilterBar
│   │   ├── ChipSelect (status)
│   │   ├── ChipSelect (agencies)
│   │   └── RangeSlider (days_until_deadline)
│   ├── WatchlistGrid
│   │   └── TenderCard × N
│   │       ├── title
│   │       ├── agency
│   │       ├── deadline
│   │       ├── days_until
│   │       ├── changes_count
│   │       ├── Button (View)
│   │       └── Button (Remove)
│   └── WatchlistSummary
│       ├── KpiCard (total_watched)
│       ├── KpiCard (deadline_soon)
│       └── KpiCard (recent_changes)
└── AiDock
    ├── AgentCard (Discovery Agent)
    └── EvidencePanel (watchlist insights)
```

## Data Sources

### Watchlist
```typescript
// API: GET /api/v1/tenders/watchlist
interface Watchlist {
  tenders: WatchlistTender[];
  total_count: number;
}

interface WatchlistTender {
  tender_id: string;
  title: string;
  agency: string;
  zone: string;
  submission_deadline: string;
  days_until: number;
  changes_count: number;
  last_checked: string;
  notifications_enabled: boolean;
}
```

### React Query
```typescript
const { data: watchlist } = useQuery({
  queryKey: ['tenders', 'watchlist', filters],
  queryFn: () => api.get('/api/v1/tenders/watchlist', { params: filters }),
  refetchInterval: 60_000, // 1 minute
});

const addToWatchlist = useMutation({
  mutationFn: (tenderId: string) => api.post(`/api/v1/tenders/watchlist/${tenderId}`),
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ['tenders', 'watchlist'] });
    toast.success('Added to watchlist');
  },
});

const removeFromWatchlist = useMutation({
  mutationFn: (tenderId: string) => api.delete(`/api/v1/tenders/watchlist/${tenderId}`),
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ['tenders', 'watchlist'] });
    toast.success('Removed from watchlist');
  },
});
```

## Zustand Store
```typescript
// stores/watchlistStore.ts
interface WatchlistState {
  filters: {
    status: string[];
    agencies: string[];
    maxDaysUntil: number;
  };
  setFilter: <K extends keyof WatchlistState['filters']>(key: K, value: WatchlistState['filters'][K]) => void;
}
```

## Interactions

### View Tender
1. Click tender card
2. Open TenderDetail drawer
3. View full details
4. Take action

### Remove from Watchlist
1. Click Remove button
2. Confirm removal
3. Remove from list
4. Update count

### Filter Watchlist
1. Apply filter
2. Refetch watchlist
3. Update grid
4. Preserve selections

### Toggle Notifications
1. Click notification bell
2. Toggle notifications
3. Save preference
4. Update status

## Responsive Breakpoints

| Breakpoint | Layout |
|------------|--------|
| Desktop (>1024px) | Grid cards with filters |
| Tablet (768-1024px) | Stacked cards |
| Mobile (<768px) | List view, swipe actions |

## Loading States
- Watchlist: Skeleton cards
- Summary: Skeleton cards
- Filter: Skeleton chips

## Error States
- Load failure: Retry button
- Remove failure: Toast error
- Network error: Toast notification

## Accessibility
- Cards are focusable
- Changes announced via `aria-live`
- Screen reader: "Tender X, deadline in 5 days"
- Keyboard: Enter to view, Delete to remove

## Telemetry
- `watchlist.view` — Screen loaded
- `watchlist.add` — Tender added
- `watchlist.remove` — Tender removed
- `watchlist.filter` — Filter applied

## Implementation Notes
- Grid layout for tender cards
- Real-time change tracking
- Notification system
- AiDock provides watchlist insights
- Export for monitoring
