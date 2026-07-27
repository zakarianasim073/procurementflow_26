# EXEC-021: Activity Feed Screen Specification

**Module:** `features/activity-feed/ActivityFeedPage`
**Layer:** features
**Version:** 1.0.0
**Status:** Draft
**Workspace:** Dashboard

## Purpose
Real-time activity feed, notifications, and event stream.

## Screen Layout

```
┌─────────────────────────────────────────────────────────────┐
│ ExecutiveHeader                                             │
├──────────┬──────────────────────────────────────────────────┤
│          │ Breadcrumb: Dashboard > Activity Feed             │
│ Workspace├──────────────────────────────────────────────────┤
│   Nav    │ ActivityFeedHeader (count, unread)               │
│          ├──────────────────────────────────────────────────┤
│          │ ActivityFeed (main content)                      │
│          │ ┌────────────────────────────────────────────┐   │
│          │ │ FilterBar (type, user, date)                │   │
│          │ ├────────────────────────────────────────────┤   │
│          │ │ FeedList (activity entries)                 │   │
│          │ │ ┌──────────────────────────────────────────┐│   │
│          │ │ │ ● User A created tender at 10:00         ││   │
│          │ │ │ ● User B uploaded BOQ at 10:05           ││   │
│          │ │ │ ...                                      ││   │
│          │ │ └──────────────────────────────────────────┘│   │
│          │ ├────────────────────────────────────────────┤   │
│          │ │ ActivityDetails (selected activity)         │   │
│          │ └────────────────────────────────────────────┘   │
├──────────┴──────────────────────────────────────────────────┤
│ AiDock (activity insights)                                  │
└─────────────────────────────────────────────────────────────┘
```

## Component Tree

```
ActivityFeedPage
├── ExecutiveHeader
├── Breadcrumb
├── ActivityFeedHeader
│   ├── KpiStrip (activity_count, unread_count)
│   └── Button (Mark All Read)
├── ActivityFeed
│   ├── FilterBar
│   │   ├── ChipSelect (activity_type)
│   │   ├── ChipSelect (user)
│   │   └── CalendarRange (date_range)
│   ├── FeedList
│   │   └── VirtualList<ActivityEntry>
│   │       └── ActivityCard × N
│   │           ├── user
│   │           ├── action
│   │           ├── target
│   │           ├── timestamp
│   │           └── read_status
│   ├── ActivityDetails
│   │   ├── activity_info
│   │   ├── related_items
│   │   └── context
│   └── ActivityStats
│       ├── chart (activity_trend)
│       ├── chart (by_user)
│       └── chart (by_type)
└── AiDock
    ├── AgentCard (Activity Agent)
    └── EvidencePanel (activity insights)
```

## Data Sources

### Activity Feed
```typescript
// API: GET /api/v1/activities
interface ActivityFeed {
  activities: ActivityEntry[];
  total_count: number;
  unread_count: number;
}

interface ActivityEntry {
  activity_id: string;
  user_id: string;
  user_name: string;
  action: string;
  target_type: string;
  target_id: string;
  target_name: string;
  timestamp: string;
  read: boolean;
  metadata?: Record<string, any>;
}
```

### React Query
```typescript
const { data: feed } = useQuery({
  queryKey: ['activities', filters],
  queryFn: () => api.get('/api/v1/activities', { params: filters }),
  refetchInterval: 30_000,
});

const markRead = useMutation({
  mutationFn: (activityId: string) => api.patch(`/api/v1/activities/${activityId}`, { read: true }),
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ['activities'] });
  },
});

const markAllRead = useMutation({
  mutationFn: () => api.post('/api/v1/activities/mark-all-read'),
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ['activities'] });
    toast.success('All activities marked as read');
  },
});
```

## Zustand Store
```typescript
// stores/activityFeedStore.ts
interface ActivityFeedState {
  filters: {
    activity_type: string[];
    user: string[];
    date_range: { start: string; end: string } | null;
  };
  setFilter: <K extends keyof ActivityFeedState['filters']>(key: K, value: ActivityFeedState['filters'][K]) => void;
}
```

## Interactions

### View Activity
1. Click activity card
2. View details
3. Check related items
4. Review context

### Filter Feed
1. Apply filter
2. Update list
3. Preserve selection
4. Refresh display

### Mark Read
1. Click activity
2. Mark as read
3. Update count
4. Refresh list

### Mark All Read
1. Click Mark All Read
2. Update all activities
3. Refresh count
4. Update UI

## Responsive Breakpoints

| Breakpoint | Layout |
|------------|--------|
| Desktop (>1024px) | Full feed + details |
| Tablet (768-1024px) | Feed with modal details |
| Mobile (<768px) | Simplified feed |

## Loading States
- Feed: Skeleton cards
- Details: Loading spinner
- Stats: Loading charts

## Error States
- Load failure: Retry button
- Mark read failure: Toast error
- Network error: Toast notification

## Accessibility
- Activities are focusable
- Count announced via `aria-live`
- Screen reader: "Activity: User A created tender"
- Keyboard: Arrow keys to navigate

## Telemetry
- `activity_feed.view` — Screen loaded
- `activity_feed.mark_read` — Activity read
- `activity_feed.mark_all_read` — All read
- `activity_feed.filter` — Filter applied

## Implementation Notes
- Real-time activity feed
- Filtering and search
- Read/unread tracking
- AiDock provides activity insights
- Export for analysis
