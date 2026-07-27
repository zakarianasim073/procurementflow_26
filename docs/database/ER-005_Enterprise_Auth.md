# ER-005: Enterprise & Auth Domain

```mermaid
erDiagram
    users {
        uuid id PK
        varchar email UK
        text password_hash
        text full_name
        varchar role "admin/manager/analyst/viewer"
        varchar tenant_id FK
        boolean active
        timestamp last_login
        timestamp created_at
    }

    refresh_tokens {
        uuid id PK
        varchar user_id FK
        varchar token_hash
        timestamp expires_at
        boolean revoked
        timestamp created_at
    }

    rbac_roles {
        varchar role_name PK
        text description
        jsonb permissions
        timestamp created_at
    }

    rbac_permissions {
        varchar permission_id PK
        varchar resource
        varchar action "read/write/delete/execute"
        text description
    }

    role_permissions {
        varchar role_name FK
        varchar permission_id FK
    }

    audit_events {
        uuid id PK
        varchar user_id FK
        varchar tenant_id FK
        varchar action
        varchar resource_type
        varchar resource_id
        jsonb details
        inet ip_address
        timestamp created_at
    }

    webhook_registrations {
        uuid id PK
        varchar tenant_id FK
        varchar event_type
        varchar url
        varchar secret_hash
        boolean active
        integer failure_count
        timestamp last_triggered
        timestamp created_at
    }

    retention_policies {
        uuid id PK
        varchar tenant_id FK
        varchar resource_type
        integer retention_days
        text action "delete/archive"
        boolean active
        timestamp created_at
    }

    users ||--o{ refresh_tokens : "has refresh tokens"
    users ||--o{ audit_events : "creates audit events"
    users }o--|| rbac_roles : "has role"
    rbac_roles ||--o{ role_permissions : "has permissions"
    rbac_permissions ||--o{ role_permissions : "granted to roles"
    webhook_registrations }o--|| users : "registered by"
```

## RBAC Matrix

| Role | Resources | Actions |
|------|-----------|---------|
| `admin` | * | * |
| `manager` | tenders, boq, agents, reports | read, write, execute |
| `analyst` | tenders, boq, reports, analytics | read |
| `viewer` | tenders, reports | read |

## Audit Event Schema

```json
{
  "id": "uuid",
  "user_id": "uuid",
  "tenant_id": "uuid",
  "action": "boq.compare",
  "resource_type": "boq_comparison",
  "resource_id": "123",
  "details": { "tender_id": "1298004", "items_count": 45 },
  "ip_address": "192.168.1.1",
  "created_at": "2026-07-24T02:00:00Z"
}
```

## Token Lifecycle

| Token | TTL | Storage | Refresh |
|-------|-----|---------|---------|
| Access Token | 15 min | Memory/cookie | No |
| Refresh Token | 7 days | DB (refresh_tokens) | Yes (one-time use) |
| SSO Token | IdP-dependent | Session | Via IdP |
