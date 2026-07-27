# EXEC-016: Notifications Dashboard Screen Specification

**Module:** `features/notifications-dashboard/NotificationsDashboardPage`
**Layer:** features
**Version:** 1.0.0
**Status:** Draft
**Workspace:** Dashboard

## Purpose
Centralized notification management, preferences, and history.

## Screen Layout

```
┌─────────────────────────────────────────────────────────────┐
│ ExecutiveHeader                                             │
├──────────┬──────────────────────────────────────────────────┤
│          │ Breadcrumb: Dashboard > Notifications Dashboard   │
│ Workspace├──────────────────────────────────────────────────┤
│   Nav    │ NotificationsDashboardHeader (count, unread)     │
│          ├──────────────────────────────────────────────────┤
│          │ NotificationsDashboard (main content)            │
│          │ ┌────────────────────────────────────────────┐   │
│          │ │ Tabs: [All] [Unread] [Settings] [History]  │   │
│          │ ├────────────────────────────────────────────┤   │
│          │ │ NotificationList (notifications)            │   │
│          │ │ NotificationSettings (preferences)          │   │
│          │ │ NotificationHistory (past notifications)    │   │
│          │ └────────────────────────────────────────────┘   │
├──────────┴──────────────────────────────────────────────────┤
│ AiDock (notification insights)                              │
└─────────────────────────────────────────────────────────────┘
```

## Component Tree

```
NotificationsDashboardPage
├── ExecutiveHeader
├── Breadcrumb
├── NotificationsDashboardHeader
│   ├── KpiStrip (total_count, unread_count)
│   └── Button (Mark All Read)
├── NotificationsDashboard
│   ├── Tabs
│   │   ├── AllTab
│   │   │   └── NotificationList
│   │   │       └── NotificationCard × N
│   │   │           ├── type
│   │   │           ├── title
│   │   │           ├── message
│   │   │           ├── timestamp
│   │   │           ├── read_status
│   │   │           └── actions (mark_read, delete)
│   │   ├── UnreadTab
│   │   │   └── NotificationList (filtered)
│   │   ├── SettingsTab
│   │   │   └── NotificationSettings
│   │   │       ├── email_preferences
│   │   │       ├── push_preferences
│   │   │       ├── in_app_preferences
│   │   │       └── quiet_hours
│   │   └── HistoryTab
│   │       └── NotificationHistory
│   │           └── HistoryEntry × N
│   │               ├── date
│   │               ├── type
│   │               └── status
│   └── NotificationStats
│       ├── chart (notifications_over_time)
│       └── chart (by_type)
└── AiDock
    ├── AgentCard (Notification Agent)
    └── EvidencePanel (notification insights)
```

## Data Sources

### Notifications
```typescript
// API: GET /api/v1/notifications
interface NotificationList {
  notifications: Notification[];
  total_count: number;
  unread_count: number;
}

interface Notification {
  notification_id: string;
  type: string;
  title: string;
  message: string;
  read: boolean;
  timestamp: string;
  metadata?: Record<string, any>;
}
```

### React Query
```typescript
const { data: notifications } = useQuery({
  queryKey: ['notifications'],
  queryFn: () => api.get('/api/v1/notifications'),
  refetchInterval: 30_000,
});

const markRead = useMutation({
  mutationFn: (notificationId: string) => api.patch(`/api/v1/notifications/${notificationId}`, { read: true }),
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ['notifications'] });
  },
});

const markAllRead = useMutation({
  mutationFn: () => api.post('/api/v1/notifications/mark-all-read'),
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ['notifications'] });
    toast.success('All notifications marked as read');
  },
});
```

## Zustand Store
```typescript
// stores/notificationsDashboardStore.ts
interface NotificationsDashboardState {
  activeTab: string;
  setTab: (tab: string) => void;
}
```

## Interactions

### View Notification
1. Click notification card
2. View details
3. Mark as read
4. Take action

### Mark All Read
1. Click Mark All Read
2. Update all notifications
3. Refresh count
4. Update UI

### Change Settings
1. Click Settings tab
2. Modify preferences
3. Save changes
4. Confirm update

### Delete Notification
1. Click Delete button
2. Confirm deletion
3. Remove notification
4. Update list

## Responsive Breakpoints

| Breakpoint | Layout |
|------------|--------|
| Desktop (>1024px) | Full tabs + list |
| Tablet (768-1024px) | Stacked tabs |
| Mobile (<768px) | Simplified list |

## Loading States
- Notifications: Skeleton cards
- Settings: Loading form
- History: Loading entries

## Error States
- Load failure: Retry button
- Mark read failure: Toast error
- Network error: Toast notification

## Accessibility
- Notifications are focusable
- Unread count announced via `aria-live`
- Screen reader: "Notification: New tender found, unread"
- Keyboard: Arrow keys to navigate

## Telemetry
- `notifications_dashboard.view` — Screen loaded
- `notifications_dashboard.mark_read` — Notification read
- `notifications_dashboard.mark_all_read` — All read
- `notifications_dashboard.settings_change` — Settings changed

## Implementation Notes
- Real-time notifications
- Multiple notification types
- User preferences
- AiDock provides notification insights
- Quiet hours support
