# ENT-006: Notifications Screen Specification

**Module:** `features/notifications/NotificationsPage`
**Layer:** features
**Version:** 1.0.0
**Status:** Draft
**Workspace:** Settings

## Purpose
Notification management, preference configuration, and notification history viewing.

## Screen Layout

```
┌─────────────────────────────────────────────────────────────┐
│ ExecutiveHeader                                             │
├──────────┬──────────────────────────────────────────────────┤
│          │ Breadcrumb: Settings > Notifications              │
│ Workspace├──────────────────────────────────────────────────┤
│   Nav    │ NotificationsHeader (unread count, preferences)  │
│          ├──────────────────────────────────────────────────┤
│          │ NotificationsManager (main content)              │
│          │ ┌────────────────────────────────────────────┐   │
│          │ │ Tabs: [Inbox] [History] [Preferences]      │   │
│          │ ├────────────────────────────────────────────┤   │
│          │ │ NotificationList (unread/recent)            │   │
│          │ │ NotificationHistory (past notifications)    │   │
│          │ │ PreferencesForm (settings)                  │   │
│          │ └────────────────────────────────────────────┘   │
├──────────┴──────────────────────────────────────────────────┤
│ AiDock (notification insights, digest suggestions)          │
└─────────────────────────────────────────────────────────────┘
```

## Component Tree

```
NotificationsPage
├── ExecutiveHeader
├── Breadcrumb
├── NotificationsHeader
│   ├── Badge (unread_count)
│   ├── Button (Mark All Read)
│   └── Button (Preferences)
├── NotificationsManager
│   ├── Tabs
│   │   ├── InboxTab
│   │   │   └── NotificationList
│   │   │       └── NotificationItem × N
│   │   │           ├── icon
│   │   │           ├── title
│   │   │           ├── message
│   │   │           ├── timestamp
│   │   │           └── read/unread
│   │   ├── HistoryTab
│   │   │   └── NotificationHistory
│   │   │       └── Table<Notification>
│   │   │           ├── timestamp
│   │   │           ├── type
│   │   │           ├── title
│   │   │           └── status
│   │   └── PreferencesTab
│   │       └── PreferencesForm
│   │           ├── Switch (email_enabled)
│   │           ├── Switch (push_enabled)
│   │           ├── Switch (sms_enabled)
│   │           └── NotificationPreferences (per type)
│   └── NotificationDetail
│       ├── title
│       ├── message
│       ├── timestamp
│       └── actions (view, dismiss, archive)
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
  created_at: string;
  action_url?: string;
  metadata?: Record<string, any>;
}
```

### Preferences
```typescript
// API: GET /api/v1/notifications/preferences
interface NotificationPreferences {
  email_enabled: boolean;
  push_enabled: boolean;
  sms_enabled: boolean;
  preferences: {
    type: string;
    email: boolean;
    push: boolean;
    sms: boolean;
  }[];
}
```

### React Query
```typescript
const { data: notifications } = useQuery({
  queryKey: ['notifications'],
  queryFn: () => api.get('/api/v1/notifications'),
  refetchInterval: 30_000, // 30 seconds
});

const { data: preferences } = useQuery({
  queryKey: ['notifications', 'preferences'],
  queryFn: () => api.get('/api/v1/notifications/preferences'),
});

const markAsRead = useMutation({
  mutationFn: (notificationId: string) =>
    api.patch(`/api/v1/notifications/${notificationId}`, { read: true }),
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ['notifications'] });
  },
});

const markAllRead = useMutation({
  mutationFn: () => api.post('/api/v1/notifications/read-all'),
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ['notifications'] });
    toast.success('All notifications marked as read');
  },
});

const updatePreferences = useMutation({
  mutationFn: (request: UpdatePreferencesRequest) =>
    api.patch('/api/v1/notifications/preferences', request),
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ['notifications', 'preferences'] });
    toast.success('Preferences updated');
  },
});
```

## Zustand Store
```typescript
// stores/notificationsStore.ts
interface NotificationsState {
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

### Archive Notification
1. Click archive button
2. Remove from inbox
3. Move to history
4. Update counts

## Responsive Breakpoints

| Breakpoint | Layout |
|------------|--------|
| Desktop (>1024px) | Full tabs with list |
| Tablet (768-1024px) | Stacked tabs |
| Mobile (<768px) | Single tab view |

## Loading States
- Notifications: Skeleton list
- Preferences: Skeleton form
- History: Skeleton table

## Error States
- Load failure: Retry button
- Save failure: Toast error
- Network error: Retry button

## Accessibility
- Notifications are focusable
- Unread count announced via `aria-live`
- Screen reader: "Notification X, unread"
- Keyboard: Enter to open, Delete to archive

## Telemetry
- `notifications.view` — Screen loaded
- `notifications.mark_read` — Notification read
- `notifications.mark_all_read` — All marked read
- `notifications.preference_change` — Preference updated

## Implementation Notes
- Real-time notification updates
- Preference management per type
- Notification history with search
- AiDock provides notification insights
- Export for audit trail
