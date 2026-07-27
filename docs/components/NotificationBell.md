# NotificationBell Component Contract

**Package**: `widgets/notifications`  
**Type**: Notification Component  
**Stability**: Stable  

---

## Purpose

Notification bell icon with dropdown for viewing and managing notifications. Includes unread count badge, real-time updates, and quick actions.

---

## Props

```typescript
interface NotificationBellProps {
  /** Notifications */
  notifications: Notification[];
  /** Unread count */
  unreadCount?: number;
  /** Mark as read handler */
  onMarkAsRead?: (id: string) => void;
  /** Mark all as read handler */
  onMarkAllAsRead?: () => void;
  /** Dismiss handler */
  onDismiss?: (id: string) => void;
  /** View all handler */
  onViewAll?: () => void;
  /** Max visible */
  maxVisible?: number; // default: 5
  /** Show unread badge */
  showBadge?: boolean; // default: true
  /** Real-time updates */
  realtime?: boolean;
  /** Custom className */
  className?: string;
}

interface Notification {
  id: string;
  type: 'info' | 'success' | 'warning' | 'error' | 'system';
  title: string;
  message?: string;
  timestamp: Date | string;
  read: boolean;
  action?: {
    label: string;
    onClick: () => void;
    variant?: 'primary' | 'secondary';
  };
  metadata?: {
    tenderId?: string;
    agentId?: string;
    reportId?: string;
    url?: string;
  };
}
```

---

## Slots

| Slot | Required | Description |
|------|----------|-------------|
| `item` | No | Custom notification rendering |
| `empty` | No | Empty state |
| `footer` | No | "View all" link |

---

## State

| State | Visual |
|-------|--------|
| `closed` | Bell icon only |
| `open` | Dropdown with list |
| `loading` | Skeleton items |
| `empty` | "No notifications" |
| `unread` | Blue dot on bell |

---

## Accessibility

- **Role**: `menu` with `aria-label="Notifications"`
- **Button**: `aria-label="Notifications, [count] unread"`
- **Items**: `role="menuitem"` with `aria-read`
- **Focus Trap**: Within dropdown
- **Keyboard**: Full navigation

---

## Keyboard

| Key | Action |
|-----|--------|
| `Tab` | Focus bell → items |
| `Enter` / `Space` | Open/close |
| `Arrow Down/Up` | Navigate items |
| `Enter` | Open notification |
| `Escape` | Close dropdown |
| `R` | Mark as read |
| `D` | Dismiss |

---

## Usage Examples

```tsx
// Basic
<NotificationBell
  notifications={notifications}
  unreadCount={unreadCount}
  onMarkAsRead={markAsRead}
  onMarkAllAsRead={markAllAsRead}
  onDismiss={dismiss}
  onViewAll={() => router.push('/notifications')}
/>

// With real-time
<NotificationBell
  notifications={notifications}
  unreadCount={unreadCount}
  realtime
  maxVisible={10}
  onMarkAsRead={markAsRead}
/>

// Custom item
<NotificationBell
  notifications={notifications}
  renderItem={(notification) => (
    <NotificationItem
      notification={notification}
      onRead={markAsRead}
      onDismiss={dismiss}
    />
  )}
/>
```

---

## NotificationItem Component

```tsx
interface NotificationItemProps {
  notification: Notification;
  onRead: (id: string) => void;
  onDismiss: (id: string) => void;
}

const NotificationItem = ({ notification, onRead, onDismiss }) => (
  <Flex
    gap={3}
    className={cn(
      'p-3 gap-3',
      !notification.read && 'bg-primary/5'
    )}
  >
    <div className={cn(
      'w-10 h-10 rounded-full flex items-center justify-center flex-shrink-0',
      notification.type === 'success' && 'bg-green-100 text-green-600',
      notification.type === 'error' && 'bg-red-100 text-red-600',
      notification.type === 'warning' && 'bg-amber-100 text-amber-600',
      notification.type === 'info' && 'bg-blue-100 text-blue-600',
      notification.type === 'system' && 'bg-gray-100 text-gray-600'
    )}>
      {notification.type === 'success' && <CheckCircle className="w-5 h-5" />}
      {notification.type === 'error' && <AlertCircle className="w-5 h-5" />}
      {notification.type === 'warning' && <AlertTriangle className="w-5 h-5" />}
      {notification.type === 'info' && <Info className="w-5 h-5" />}
      {notification.type === 'system' && <Cpu className="w-5 h-5" />}
    </div>
    <Flex flexDir="column" flex={1} minWidth={0} gap={1}>
      <Flex justify="between">
        <Text weight="medium" className={cn(
          !notification.read && 'font-semibold'
        )}>
          {notification.title}
        </Text>
        <Text size="xs" className="text-muted">
          {formatDistanceToNow(new Date(notification.timestamp), { addSuffix: true })}
        </Text>
      </Flex>
      {notification.message && (
        <Text size="sm" className="text-muted line-clamp-2">
          {notification.message}
        </Text>
      )}
      {notification.action && (
        <Button
          variant="ghost"
          size="sm"
          onClick={notification.action.onClick}
        >
          {notification.action.label}
        </Button>
      )}
    </Flex>
    <Flex flexDir="column" gap={1}>
      {!notification.read && (
        <Button
          variant="ghost"
          size="icon"
          onClick={() => onRead(notification.id)}
          aria-label="Mark as read"
        >
          <Check className="w-4 h-4" />
        </Button>
      )}
      <Button
        variant="ghost"
        size="icon"
        onClick={() => onDismiss(notification.id)}
        aria-label="Dismiss"
      >
        <X className="w-4 h-4" />
      </Button>
    </Flex>
  </Flex>
);
```

---

## Real-time Updates

```tsx
// WebSocket integration
useEffect(() => {
  const ws = new WebSocket('/ws/notifications');
  
  ws.onmessage = (event) => {
    const notification = JSON.parse(event.data);
    setNotifications(prev => [notification, ...prev]);
    setUnreadCount(prev => prev + 1);
  };
  
  return () => ws.close();
}, []);
```

---

## Permissions

| Role | View | Mark Read | Dismiss |
|------|------|-----------|---------|
| `viewer` | ✅ | Own | Own |
| `estimator` | ✅ | Own | Own |
| `admin` | ✅ | All | All |

---

## Future Extensions

- [ ] Group by date
- [ ] Filter by type
- [ ] Snooze notifications
- [ ] Email digest
- [ ] Push notifications
- [ ] Notification preferences