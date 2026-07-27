# EXEC-006: Notifications Dashboard Screen Specification

**Module:** `features/notifications-dashboard/NotificationsDashboardPage`
**Layer:** features
**Version:** 1.0.0
**Status:** Draft
**Workspace:** Dashboard

## Purpose
Notification center with overview, preferences, and notification management.

## Screen Layout

```
┌─────────────────────────────────────────────────────────────┐
│ ExecutiveHeader                                             │
├──────────┬──────────────────────────────────────────────────┤
│          │ Breadcrumb: Dashboard > Notifications             │
│ Workspace├──────────────────────────────────────────────────┤
│   Nav    │ NotificationsDashboardHeader (unread, filters)   │
│          ├──────────────────────────────────────────────────┤
│          │ NotificationsDashboard (main content)            │
│          │ ┌────────────────────────────────────────────┐   │
│          │ │ Tabs: [Inbox] [Unread] [Archived] [Prefs]  │   │
│          │ ├────────────────────────────────────────────┤   │
│          │ │ NotificationList (grouped by date)          │   │
│          │ │ NotificationDetail (selected notification)  │   │
│          │ │ PreferencesForm (notification settings)     │   │
│          │ └────────────────────────────────────────────┘   │
├──────────┴──────────────────────────────────────────────────┤
│ AiDock (notification insights, digest suggestions)          │
└─────────────────────────────────────────────────────────────┘
```

## Component Tree

```
NotificationsDashboardPage
├── ExecutiveHeader
├── Breadcrumb
├── NotificationsDashboardHeader
│   ├── Badge (unread_count)
│   ├── ChipSelect (types)
│   └── Button (Mark All Read)
├── NotificationsDashboard
│   ├── Tabs
│   │   ├── InboxTab
│   │   │   └── NotificationList
│   │   │       └── NotificationGroup × N
│   │   │           ├── date
│   │   │           └── NotificationItem × N
│   │   │               ├── icon
│   │   │               ├── title
│   │   │               ├── message
│   │   │               ├── timestamp
│   │   │               └── read/unread
│   │   ├── UnreadTab
│   │   │   └── NotificationList (filtered)
│   │   ├── ArchivedTab
│   │   │   └── NotificationList (archived)
│   │   └── PrefsTab
│   │       └── PreferencesForm
│   │           ├── Switch (email_enabled)
│   │           ├── Switch (push_enabled)
│   │           └── NotificationPreferences (per type)
│   └── NotificationDetail
│       ├── title
│       ├── message
│       ├── timestamp
│       └── actions (archive, delete, mark_read)
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
  unread_count: number;
  total_count: number;
}

interface Notification {
  notification_id: string;
  type: string;
  title: string;
  message: string;
  read: boolean;
  archived: boolean;
  created_at: string;
  action_url?: string;
}
```

### React Query
```typescript
const { data: notifications } = useQuery({
  queryKey: ['notifications', filters],
  queryFn: () => api.get('/api/v1/notifications', { params: filters }),
  refetchInterval: 30_000, // 30 seconds
});

const markAsRead = useMutation({
  mutationFn: (notificationId: string) =>
    api.patch(`/api/v1/notifications/${notificationId}`, { read: true }),
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ['notifications'] });
  },
});

const archiveNotification = useMutation({
  mutationFn: (notificationId: string) =>
    api.patch(`/api/v1/notifications/${notificationId}`, { archived: true }),
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ['notifications'] });
    toast.success('Notification archived');
  },
});
```

## Zustand Store
```typescript
// stores/notificationsDashboardStore.ts
interface NotificationsDashboardState {
  activeTab: string;
  selectedNotification: string | null;
  setTab: (tab: string) => void;
  setSelected: (id: string | null) => void;
}
```

## Interactions

### View Notification
1. Click notification item
2. Open NotificationDetail
3. Mark as read
4. Navigate to action_url

### Archive Notification
1. Click archive button
2. Remove from inbox
3. Move to archived
4. Update counts

### Mark All Read
1. Click "Mark All Read"
2. Confirm action
3. Update all notifications
4. Refresh unread count

### Update Preferences
1. Toggle notification type
2. Auto-save preference
3. Show confirmation
4. Update notification system

## Responsive Breakpoints

| Breakpoint | Layout |
|------------|--------|
| Desktop (>1024px) | Full tabs with list |
| Tablet (768-1024px) | Stacked tabs |
| Mobile (<768px) | Single tab view |

## Loading States
- Notifications: Skeleton list
- Preferences: Skeleton form
- Detail: Skeleton content

## Error States
- Load failure: Retry button
- Update failure: Toast error
- Network error: Retry button

## Accessibility
- Notifications are focusable
- Unread count announced via `aria-live`
- Screen reader: "Notification X, unread"
- Keyboard: Enter to open, Delete to archive

## Telemetry
- `notifications_dashboard.view` — Screen loaded
- `notifications_dashboard.mark_read` — Notification read
- `notifications_dashboard.archive` — Notification archived
- `notifications_dashboard.preference_change` — Preference updated

## Implementation Notes
- Real-time notification updates
- Grouped by date for easy scanning
- Preference management per type
- AiDock provides notification insights
- Export for audit trail
