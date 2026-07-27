# OPP-009: Saved Searches Screen Specification

**Module:** `features/saved-searches/SavedSearchesPage`
**Layer:** features
**Version:** 1.0.0
**Status:** Draft
**Workspace:** Discovery

## Purpose
Manage saved search queries, notifications, and search analytics.

## Screen Layout

```
┌─────────────────────────────────────────────────────────────┐
│ ExecutiveHeader                                             │
├──────────┬──────────────────────────────────────────────────┤
│          │ Breadcrumb: Discovery > Saved Searches            │
│ Workspace├──────────────────────────────────────────────────┤
│   Nav    │ SavedSearchesHeader (count, notifications)       │
│          ├──────────────────────────────────────────────────┤
│          │ SavedSearches (main content)                     │
│          │ ┌────────────────────────────────────────────┐   │
│          │ │ Tabs: [Searches] [Notifications] [Analytics]│  │
│          │ ├────────────────────────────────────────────┤   │
│          │ │ SearchList (saved search cards)             │   │
│          │ │ NotificationSettings (alert config)         │   │
│          │ │ SearchAnalytics (usage stats)               │   │
│          │ └────────────────────────────────────────────┘   │
├──────────┴──────────────────────────────────────────────────┤
│ AiDock (search suggestions, optimization)                   │
└─────────────────────────────────────────────────────────────┘
```

## Component Tree

```
SavedSearchesPage
├── ExecutiveHeader
├── Breadcrumb
├── SavedSearchesHeader
│   ├── KpiStrip (search_count, notification_count)
│   └── Button (New Search)
├── SavedSearches
│   ├── Tabs
│   │   ├── SearchesTab
│   │   │   └── SearchList
│   │   │       └── SearchCard × N
│   │   │           ├── name
│   │   │           ├── query
│   │   │           ├── filters
│   │   │           ├── result_count
│   │   │           ├── last_run
│   │   │           └── actions (run, edit, delete)
│   │   ├── NotificationsTab
│   │   │   └── NotificationSettings
│   │   │       └── Table<SavedSearch>
│   │   │           ├── name
│   │   │           ├── email_notify
│   │   │           ├── push_notify
│   │   │           └── Button (Toggle)
│   │   └── AnalyticsTab
│   │       └── SearchAnalytics
│   │           ├── Chart (searches_over_time)
│   │           ├── Chart (by_type)
│   │           └── Table (top_searches)
│   └── SearchDetail
│       ├── query_info
│       ├── results_preview
│       └── actions (run, share, export)
└── AiDock
    ├── AgentCard (Search Agent)
    └── EvidencePanel (search insights)
```

## Data Sources

### Saved Searches
```typescript
// API: GET /api/v1/tenders/saved-searches
interface SavedSearchList {
  searches: SavedSearch[];
  total_count: number;
}

interface SavedSearch {
  search_id: string;
  name: string;
  query: string;
  filters: Record<string, any>;
  result_count: number;
  last_run: string;
  created_at: string;
  notifications_enabled: boolean;
  email_notify: boolean;
  push_notify: boolean;
}
```

### React Query
```typescript
const { data: searches } = useQuery({
  queryKey: ['tenders', 'saved-searches'],
  queryFn: () => api.get('/api/v1/tenders/saved-searches'),
});

const runSearch = useMutation({
  mutationFn: (searchId: string) => api.post(`/api/v1/tenders/saved-searches/${searchId}/run`),
  onSuccess: () => {
    toast.success('Search executed');
  },
});

const deleteSearch = useMutation({
  mutationFn: (searchId: string) => api.delete(`/api/v1/tenders/saved-searches/${searchId}`),
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ['tenders', 'saved-searches'] });
    toast.success('Search deleted');
  },
});

const toggleNotifications = useMutation({
  mutationFn: ({ searchId, enabled }: { searchId: string; enabled: boolean }) =>
    api.patch(`/api/v1/tenders/saved-searches/${searchId}`, { notifications_enabled: enabled }),
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ['tenders', 'saved-searches'] });
  },
});
```

## Zustand Store
```typescript
// stores/savedSearchesStore.ts
interface SavedSearchesState {
  activeTab: string;
  setTab: (tab: string) => void;
}
```

## Interactions

### Run Search
1. Click Run button
2. Execute search
3. View results
4. Update count

### Edit Search
1. Click Edit button
2. Modify query/filters
3. Save changes
4. Update card

### Toggle Notifications
1. Click notification toggle
2. Enable/disable
3. Save preference
4. Update status

### Delete Search
1. Click Delete button
2. Confirm deletion
3. Remove from list
4. Update count

## Responsive Breakpoints

| Breakpoint | Layout |
|------------|--------|
| Desktop (>1024px) | Full tabs with cards |
| Tablet (768-1024px) | Stacked tabs |
| Mobile (<768px) | Single tab view |

## Loading States
- Searches: Skeleton cards
- Analytics: Skeleton charts
- Settings: Skeleton form

## Error States
- Run failure: Toast error
- Delete failure: Toast error
- Network error: Toast notification

## Accessibility
- Search cards are focusable
- Count announced via `aria-live`
- Screen reader: "Search X, Y results"
- Keyboard: Enter to run, Delete to remove

## Telemetry
- `saved_searches.view` — Screen loaded
- `saved_searches.run` — Search executed
- `saved_searches.delete` — Search deleted
- `saved_searches.toggle_notify` — Notifications toggled

## Implementation Notes
- Saved search management
- Notification configuration
- Search analytics
- AiDock provides search insights
- Export for analysis
