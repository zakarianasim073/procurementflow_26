# Notification API Contract

**Router**: `/api/v1/notifications`  
**Tags**: `notifications`  
**Auth**: JWT (tenant-scoped)

---

## Overview

Notification API for **in-app alerts**, **email notifications**, and **real-time updates** across the ProcureFlow platform. Core to **user engagement**, **system alerts**, and **agent event tracking**. Enables flexible notification delivery through multiple channels (push, email, in-app) with comprehensive filtering and user preferences.

**Primary Use Cases**:
- Tender status changes and milestone notifications
- Agent completion and error alerts
- System maintenance announcements
- Win probability threshold notifications
- Compliance and audit alerts
- New competitor entries

---

## Endpoint Catalog

| Method | Path | Purpose | Auth |
|--------|------|---------|------|
| GET | `/notifications` | List user notifications (paginated, filtered) | JWT |
| GET | `/notifications/{id}` | Get specific notification by ID | JWT |
| PUT | `/notifications/{id}` | Update notification (read status, preferences) | JWT |
| POST | `/notifications/send` | Send notification to users (admin) | JWT |
| POST | `/notifications/bulk-send` | Send bulk notifications (admin) | JWT |
| DELETE | `/notifications/{id}` | Delete notification | JWT |
| GET | `/notifications/stats` | Get notification statistics | JWT |
| POST | `/notifications/preferences` | Set user notification preferences | JWT |
| GET | `/notifications/preferences` | Get user notification preferences | JWT |

---

## Request/Response Schemas

### `GET /notifications`

**Query Parameters**
| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `page` | int | 1 | Page number (1-based) |
| `limit` | int | 50 | Results per page (1-200) |
| `type` | string | `""` | Filter by notification type (`system`, `agent`, `tender`, `pricing`, `competitor`, `report`, `alert`) |
| `status` | string | `""` | Filter by status (`unread`, `read`, `archived`) |
| `priority` | string | `""` | Filter by priority (`low`, `normal`, `high`, `urgent`) |
| `agent_id` | string | `""` | Filter by agent source (e.g., `agent-002`) |
| `read_at` | string | `""` | Filter by read status (e.g., `null` for unread, `notnull` for read) |

**Response (200)**
```json
{
  "success": true,
  "notifications": [
    {
      "id": "uuid",
      "title": "Tender Milestone Reached",
      "message": "Tender \"Construction of Bridge\" has been moved to the award phase",
      "type": "tender",
      "priority": "normal",
      "status": "unread",
      "category": "workflow",
      "agent_id": "agent-002-tender-acquisition",
      "agent_name": "Tender Acquisition Agent",
      "tender_id": "1298004",
      "data": {
        "tender_title": "Construction of Bridge",
        "tender_url": "/tender/1298004",
        "milestone": "award_phase",
        "deadline": "2026-08-15"
      },
      "metadata": {
        "icon": "FileText",
        "color": "blue",
        "actions": ["view_tender", "dismiss"]
      },
      "actions": [
        {
          "label": "View Tender",
          "action": "view_tender",
          "url": "/tender/1298004",
          "primary": true
        },
        {
          "label": "Dismiss",
          "action": "dismiss"
        }
      ],
      "created_at": "2026-07-21T10:30:00Z",
      "updated_at": "2026-07-21T10:30:00Z",
      "expires_at": null,
      "read_at": null,
      "tenant_id": "tenant-owner-...",
      "user_id": "user-uuid"
    }
  ],
  "pagination": {
    "page": 1,
    "limit": 50,
    "total": 247,
    "total_pages": 5,
    "has_next": true,
    "has_prev": false
  }
}
```

### `GET /notifications/{id}`

**Path Params**
- `id`: Notification UUID

**Response (200)**
```json
{
  "success": true,
  "notification": {
    "id": "uuid",
    "title": "Tender Milestone Reached",
    "message": "Tender \"Construction of Bridge\" has been moved to the award phase",
    "type": "tender",
    "priority": "normal",
    "status": "unread",
    "category": "workflow",
    "agent_id": "agent-002-tender-acquisition",
    "agent_name": "Tender Acquisition Agent",
    "tender_id": "1298004",
    "data": { ... },
    "metadata": { ... },
    "actions": [ ... ],
    "created_at": "2026-07-21T10:30:00Z",
    "updated_at": "2026-07-21T10:30:00Z",
    "expires_at": null,
    "read_at": null,
    "tenant_id": "tenant-owner-...",
    "user_id": "user-uuid"
  }
}
```

### `PUT /notifications/{id}`

**Request**
```json
{
  "status": "read",
  "action": "dismiss"
}
```

**Response (200)**
```json
{
  "success": true,
  "notification": {
    "id": "uuid",
    "title": "Tender Milestone Reached",
    "status": "read",
    "read_at": "2026-07-21T10:35:00Z"
  }
}
```

### `POST /notifications/send`

**Request**
```json
{
  "title": "System Maintenance Notice",
  "message": "ProcureFlow will be undergoing maintenance on July 25th, 2026 from 02:00 UTC to 04:00 UTC.",
  "type": "system",
  "priority": "high",
  "category": "maintenance",
  "agent_id": "system"
}
```

**Response (200)
```json
{
  "success": true,
  "notification": {
    "id": "uuid",
    "title": "System Maintenance Notice",
    "message": "ProcureFlow will be undergoing maintenance...",
    "type": "system",
    "priority": "high",
    "status": "unread",
    "category": "maintenance",
    "created_at": "2026-07-21T10:30:00Z",
    "updated_at": "2026-07-21T10:30:00Z"
  },
  "recipients": {
    "user_ids": ["user-uuid-1", "user-uuid-2"],
    "tenant_ids": ["tenant-owner-...", "tenant-admin-..."],
    "roles": ["owner", "admin"],
    "channels": ["push", "email", "in-app"]
  }
}
```

### `POST /notifications/bulk-send`

**Request**
```json
{
  "notifications": [
    {
      "title": "Tender Alert",
      "message": "New tender matching your criteria: Construction of Bridge",
      "type": "tender",
      "priority": "normal",
      "category": "discovery",
      "agent_id": "agent-001-tender-radar",
      "tender_id": "1298004",
      "recipients": {
        "user_ids": ["user-uuid-1", "user-uuid-2", "user-uuid-3"],
        "channels": ["push"]
      }
    },
    {
      "title": "System Notification",
      "message": "Weekly summary report is now available",
      "type": "system",
      "priority": "low",
      "category": "report",
      "agent_id": "system",
      "recipients": {
        "tenant_ids": ["tenant-owner-..."],
        "channels": ["email", "in-app"]
      }
    }
  ]
}
```

**Response (200)
```json
{
  "success": true,
  "results": [
    {
      "notification_id": "uuid-1",
      "recipients_count": 45,
      "channels_used": ["push", "email"],
      "status": "sent"
    },
    {
      "notification_id": "uuid-2",
      "recipients_count": 12,
      "channels_used": ["in-app"],
      "status": "sent"
    }
  ],
  "total_sent": 57,
  "total_failed": 0
}
```

### `DELETE /notifications/{id}`

**Response (200)
```json
{
  "success": true,
  "message": "Notification deleted successfully"
}
```

### `GET /notifications/stats`

**Response (200)
```json
{
  "success": true,
  "stats": {
    "total_notifications": 15478,
    "unread_count": 234,
    "archived_count": 8945,
    "by_type": {
      "system": 3421,
      "tender": 5678,
      "pricing": 2345,
      "competitor": 890,
      "report": 1234,
      "alert": 567,
      "agent": 2543
    },
    "by_priority": {
      "urgent": 89,
      "high": 567,
      "normal": 12345,
      "low": 2477
    },
    "delivery_channels": {
      "push": {"total_sent": 12345, "success_rate": 0.98},
      "email": {"total_sent": 8901, "success_rate": 0.92},
      "in_app": {"total_sent": 15478, "success_rate": 0.99}
    },
    "daily_metrics": [
      {
        "date": "2026-07-21",
        "sent": 89,
        "delivered": 87,
        "clicks": 23
      },
      {
        "date": "2026-07-20",
        "sent": 76,
        "delivered": 74,
        "clicks": 19
      }
    ]
  },
  "tenant_breakdown": {
    "tenant-owner-...": {
      "total": 5432,
      "unread": 89,
      "delivery_rate": 0.97
    }
  }
}
```

### `POST /notifications/preferences`

**Request**
```json
{
  "preferences": {
    "push": {
      "tender": true,
      "pricing": true,
      "system": true,
      "agent": false,
      "alerts": true
    },
    "email": {
      "tender": true,
      "pricing": false,
      "system": true,
      "agent": true,
      "alerts": true
    },
    "in_app": {
      "tender": true,
      "pricing": true,
      "system": false,
      "agent": true,
      "alerts": true
    },
    "quiet_hours": {
      "enabled": true,
      "start": "20:00",
      "end": "08:00"
    },
    "do_not_disturb": {
      "weekdays": ["Mon", "Tue", "Wed", "Thu", "Fri"],
      "weekend": true
    }
  }
}
```

**Response (200)
```json
{
  "success": true,
  "preferences": {
    "push": {
      "tender": true,
      "pricing": true,
      "system": true,
      "agent": false,
      "alerts": true
    },
    "email": {
      "tender": true,
      "pricing": false,
      "system": true,
      "agent": true,
      "alerts": true
    },
    "in_app": {
      "tender": true,
      "pricing": true,
      "system": false,
      "agent": true,
      "alerts": true
    },
    "quiet_hours": {
      "enabled": true,
      "start": "20:00",
      "end": "08:00"
    },
    "do_not_disturb": {
      "weekdays": ["Mon", "Tue", "Wed", "Thu", "Fri"],
      "weekend": true
    },
    "created_at": "2026-07-21T10:30:00Z",
    "updated_at": "2026-07-21T10:30:00Z"
  }
}
```

### `GET /notifications/preferences`

**Response (200)
```json
{
  "success": true,
  "preferences": {
    "push": {
      "tender": true,
      "pricing": true,
      "system": true,
      "agent": false,
      "alerts": true
    },
    "email": {
      "tender": true,
      "pricing": false,
      "system": true,
      "agent": true,
      "alerts": true
    },
    "in_app": {
      "tender": true,
      "pricing": true,
      "system": false,
      "agent": true,
      "alerts": true
    },
    "quiet_hours": {
      "enabled": true,
      "start": "20:00",
      "end": "08:00"
    },
    "do_not_disturb": {
      "weekdays": ["Mon", "Tue", "Wed", "Thu", "Fri"],
      "weekend": true
    },
    "created_at": "2026-07-21T10:30:00Z",
    "updated_at": "2026-07-21T10:30:00Z"
  }
}
```

---

## Error Codes

| Code | HTTP | Scenario |
|------|------|----------|
| `NOTIFICATION_NOT_FOUND` | 404 | Notification ID not found |
| `NOTIFICATION_ACCESS_DENIED` | 403 | User does not have permission to access notification |
| `NOTIFICATION_PREFERENCE_NOT_FOUND` | 404 | User preferences not found |
| `NOTIFICATION_SEND_FAILED` | 500 | Failed to send notification |

---

## Permission Requirements

| Endpoint | Required Role | Notes |
|----------|---------------|-------|
| `/notifications` | `viewer` | Read notifications for own tenant |
| `/notifications/{id}` | `viewer` | Access specific notification |
| `/notifications/{id}` (PUT) | `viewer` | Update notification (e.g., mark as read) |
| `/notifications/send` | `admin` | Send system-wide notifications |
| `/notifications/bulk-send` | `admin` | Send bulk notifications |
| `/notifications/stats` | `admin` | View system-wide stats |
| `/notifications/preferences` | `viewer` | Set own preferences |

---

## Rate Limits

| Endpoint | Limit | Window |
|----------|-------|--------|
| `/notifications` | 60 | 60 |
| `/notifications/{id}` | 60 | 60 |
| `/notifications/send` | 10 | 60 |
| `/notifications/bulk-send` | 5 | 60 |
| `/notifications/stats` | 30 | 60 |
| `/notifications/preferences` | 60 | 60 |

---

## Caching

- `GET /notifications/{id}`, `GET /notifications/preferences`: `private, max-age=300` (user-specific content)
- `GET /notifications/stats`: `private, max-age=60` (admin stats)
- Other: `private, max-age=30` or `no-store`

---

## React Query Mapping

```typescript
export const notificationKeys = {
  all: () => ['notifications'] as const,
  list: (params: NotificationListParams) =>
    [...notificationKeys.all, 'list', params] as const,
  detail: (id: string) => [...notificationKeys.all, 'detail', id] as const,
  stats: () => [...notificationKeys.all, 'stats'] as const,
  preferences: () => [...notificationKeys.all, 'preferences'] as const,
};

export function useNotifications(params: NotificationListParams) {
  return useQuery({
    queryKey: notificationKeys.list(params),
    queryFn: () => apiFetch<NotificationListResponse>('/notifications', { params }),
    staleTime: 30_000,
  });
}

export function useNotification(id: string) {
  return useQuery({
    queryKey: notificationKeys.detail(id),
    queryFn: () => apiFetch<NotificationDetailResponse>(`/notifications/${id}`),
    staleTime: 60_000,
  });
}

export function useNotificationStats() {
  return useQuery({
    queryKey: notificationKeys.stats(),
    queryFn: () => apiFetch<NotificationStatsResponse>('/notifications/stats'),
    staleTime: 60_000,
  });
}

export function useNotificationPreferences() {
  return useQuery({
    queryKey: notificationKeys.preferences(),
    queryFn: () => apiFetch<NotificationPreferencesResponse>('/notifications/preferences'),
    staleTime: 300_000,
  });
}

export function useUpdateNotification() {
  return useMutation({
    mutationFn: (payload: UpdateNotificationRequest) => apiFetch<NotificationDetailResponse>('/notifications/{id}', {
      method: 'PUT',
      body: JSON.stringify(payload),
    }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: notificationKeys.all }),
  });
}
```

---

## Integration Points

### Agent Notifications
```
Agent-002-tender-acquisition
  ↓ Completion notification
POST /notifications/send → notification.json

Agent-001-tender-radar
  ↓ Discovery notification
POST /notifications/send → Tenant-specific push

Agent-011-rate-analysis
  ↓ Analysis complete
UPDATE /notifications/{id} → mark as processed
```

### User Notification Preferences
```
User settings → POST /notifications/preferences

Agent events → POST /notifications/send
  └─ Filtered based on user preferences
  └─ Delivered via chosen channels (push, email, in-app)
```

### Mobile Push Integration
```
React Native mobile app
  ↓
celery notification processor
  ↓ API: POST /notifications/bulk-send
  └─ Channel-specific formatting (APNs, FCM, etc.)
```

---

## Versioning

- `v1`: Current (user notifications, preferences, admin controls)
- `v2` (planned): Real-time WebSocket push, notification workflows

---

## Configuration Options

Environment variables:
- `NOTIFICATION_MAX_DAILY_EMAILS=1000` (default: 1000)
- `NOTIFICATION_BATCH_SIZE=50` (default: 50)
- `NOTIFICATION_COOLDOWN_SECONDS=300` (default: 5 minutes)
- `NOTIFICATION_RETRY_ATTEMPTS=3` (default: 3)

---

## Monitoring & Telemetry

**Metrics**:
- Notification delivery success/failure rates
- Average processing time per notification
- Channel success rates (push, email, in-app)
- User preference compliance
- Notification click-through rates

**Alerts**:
- Delivery rate < 90%
- High failure rates (>5%)
- Notification processing time > 10 seconds

> **Integration**: `app/services/notification_service.py` (core notification delivery)
> **Queue**: Celery tasks for bulk notification processing
> **Storage**: PostgreSQL `notifications` table with tenant indexing

---

## OpenAPI Reference

See `/openapi.json#/paths/~1api~1notifications~1GET`