# EXEC-007: Activity Feed Screen Specification

**Module:** `features/activity/ActivityFeedPage`
**Layer:** features
**Version:** 1.0.0
**Status:** Draft
**Workspace:** Dashboard

## Purpose
Real-time activity feed with filters, search, and notification integration.

## Screen Layout

```
┌─────────────────────────────────────────────────────────────┐
│ ExecutiveHeader                                             │
├──────────┬──────────────────────────────────────────────────┤
│          │ Breadcrumb: Dashboard > Activity Feed             │
│ Workspace├──────────────────────────────────────────────────┤
│   Nav    │ ActivityFeedHeader (filters, search)             │
│          ├──────────────────────────────────────────────────┤
│          │ ActivityFeed (main content)                      │
│          │ ┌────────────────────────────────────────────┐   │
│          │ │ FilterBar (user, type, date)                │   │
│          │ ├────────────────────────────────────────────┤   │
│          │ │ ActivityTimeline (real-time feed)           │   │
│          │ │ ┌──────────────────────────────────────────┐│   │
│          │ │ │ ● 10:00 John created tender #123         ││   │
│          │ │ │ ● 09:50 AI analyzed BOQ for tender #456  ││   │
│          │ │ │ ● 09:45 Jane updated pricing strategy    ││   │
│          │ │ │ ...                                      ││   │
│          │ │ └──────────────────────────────────────────┘│   │
│          │ └────────────────────────────────────────────┘   │
├──────────┴──────────────────────────────────────────────────┤
│ AiDock (activity insights, trend analysis)                  │
└─────────────────────────────────────────────────────────────┘
```

## Component Tree

```
ActivityFeedPage
├── ExecutiveHeader
├── Breadcrumb
├── ActivityFeedHeader
│   ├── SearchBar (activity search)
│   ├── ChipSelect (users)
│   ├── ChipSelect (types)
│   └── CalendarRange (date range)
├── ActivityFeed
│   ├── FilterBar
│   │   ├── SearchBar (keyword)
│   │   ├── ChipSelect (user)
│   │   ├── ChipSelect (type)
│   │   └── CalendarRange (date)
│   ├── ActivityTimeline
│   │   └── ActivityItem × N
│   │       ├── avatar
│   │       ├── user_name
│   │       ├── action
│   │       ├── resource
│   │       ├── timestamp
│   │       └── details (expandable)
│   └── LoadMore
│       └── Button (Load More)
└── AiDock
    ├── AgentCard (Activity Agent)
    └── EvidencePanel (activity insights)
```

## Data Sources

### Activity Feed
```typescript
// API: GET /api/v1/activity
interface ActivityFeed {
  items: ActivityItem[];
  total_count: number;
  has_more: boolean;
}

interface ActivityItem {
  activity_id: string;
  user_id: string;
  user_name: string;
  user_avatar?: string;
  action: string;
  resource_type: string;
  resource_id: string;
  resource_name: string;
  details?: Record<string, any>;
  timestamp: string;
}
```

### React Query
```typescript
const { data: feed, fetchNextPage, hasNextPage } = useInfiniteQuery({
  queryKey: ['activity', filters],
  queryFn: ({ pageParam }) => api.get('/api/v1/activity', { params: { ...filters, page: pageParam } }),
  getNextPageParam: (lastPage) => lastPage.has_more ? lastPage.items.length : undefined,
  initialPageParam: 0,
});
```

## Zustand Store
```typescript
// stores/activityFeedStore.ts
interface ActivityFeedState {
  filters: {
    users: string[];
    types: string[];
    dateRange: { start: string; end: string } | null;
    keyword: string;
  };
  setFilter: <K extends keyof ActivityFeedState['filters']>(key: K, value: ActivityFeedState['filters'][K]) => void;
}
```

## Interactions

### Filter Activity
1. Apply filter
2. Reset pagination
3. Refetch feed
4. Update timeline

### View Details
1. Click activity item
2. Expand details
3. View resource
4. Navigate to resource

### Load More
1. Click "Load More"
2. Fetch next page
3. Append to timeline
4. Update scroll position

### Search Activity
1. Type in search bar
2. Debounce 300ms
3. Filter results
4. Update timeline

## Responsive Breakpoints

| Breakpoint | Layout |
|------------|--------|
| Desktop (>1024px) | Full timeline with filters |
| Tablet (768-1024px) | Collapsible filters |
| Mobile (<768px) | Single column, bottom filters |

## Loading States
- Timeline: Skeleton items
- Load More: Spinner
- Filter: Skeleton chips

## Error States
- Load failure: Retry button
- Network error: Toast notification
- No results: EmptyState

## Accessibility
- Activity items are focusable
- New items announced via `aria-live`
- Screen reader: "Activity: John created tender"
- Keyboard: Arrow keys to navigate, Enter to expand

## Telemetry
- `activity_feed.view` — Screen loaded
- `activity_feed.filter` — Filter applied
- `activity_feed.item_click` — Item viewed
- `activity_feed.load_more` — More loaded

## Implementation Notes
- Real-time activity feed
- Infinite scroll pagination
- Filterable by user/type/date
- AiDock provides activity insights
- Export for audit trail
