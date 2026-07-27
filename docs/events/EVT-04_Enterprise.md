# EVT-04: Enterprise Events

## user.registered

Fired when new user registers.

```json
{
  "event_type": "user.registered",
  "data": {
    "user_id": "uuid",
    "email": "user@example.com",
    "role": "analyst",
    "tenant_id": "tenant_uuid",
    "source": "registration"
  }
}
```

## user.login

Fired on successful login.

```json
{
  "event_type": "user.login",
  "data": {
    "user_id": "uuid",
    "method": "password" | "oidc" | "saml",
    "ip_address": "192.168.1.1",
    "user_agent": "Mozilla/5.0..."
  }
}
```

## audit.event

Fired on every auditable action.

```json
{
  "event_type": "audit.event",
  "data": {
    "event_id": "uuid",
    "user_id": "uuid",
    "tenant_id": "tenant_uuid",
    "action": "boq.compare",
    "resource_type": "boq_comparison",
    "resource_id": "123",
    "details": { "tender_id": "1298004" },
    "ip_address": "192.168.1.1"
  }
}
```

## webhook.delivered

Fired when webhook is successfully delivered.

```json
{
  "event_type": "webhook.delivered",
  "data": {
    "webhook_id": "uuid",
    "event_type": "tender.acquired",
    "url": "https://example.com/webhook",
    "status_code": 200,
    "duration_ms": 450
  }
}
```

## webhook.failed

Fired when webhook delivery fails after retries.

```json
{
  "event_type": "webhook.failed",
  "data": {
    "webhook_id": "uuid",
    "event_type": "tender.acquired",
    "url": "https://example.com/webhook",
    "error": "Connection refused",
    "retry_count": 3,
    "last_attempt": "2026-07-24T02:00:00Z"
  }
}
```

## quota.exceeded

Fired when tenant exceeds subscription quota.

```json
{
  "event_type": "quota.exceeded",
  "data": {
    "tenant_id": "tenant_uuid",
    "resource": "boq_comparisons",
    "used": 1000,
    "limit": 1000,
    "period": "monthly",
    "reset_at": "2026-08-01T00:00:00Z"
  }
}
```
