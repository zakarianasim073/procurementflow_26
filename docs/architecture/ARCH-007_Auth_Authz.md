# ARCH-007: Authentication & Authorization

```mermaid
sequenceDiagram
    autonumber
    actor User as Client
    participant Auth as /auth
    participant JWT as JWT Service
    participant SSO as SSO Service
    participant RBAC as RBAC Service
    participant DB as PostgreSQL

    rect rgb(240, 248, 255)
        Note over User,Auth: Registration
        User->>Auth: POST /auth/register { email, password }
        Auth->>DB: INSERT INTO users
        Auth->>JWT: generate_tokens(user_id, roles)
        JWT-->>Auth: { access_token, refresh_token }
        Auth-->>User: 201 { tokens }
    end

    rect rgb(240, 255, 240)
        Note over User,Auth: Login
        User->>Auth: POST /auth/login { email, password }
        Auth->>DB: SELECT * FROM users WHERE email=$1
        Auth->>Auth: verify_password(hash, plain)
        Auth->>JWT: generate_tokens(user_id, roles)
        JWT-->>Auth: { access_token, refresh_token }
        Auth-->>User: 200 { tokens }
    end

    rect rgb(255, 248, 240)
        Note over User,Auth: SSO Login (OIDC/SAML)
        User->>SSO: Redirect to /sso/oidc/authorize
        SSO-->>User: Authorization code
        User->>SSO: /sso/oidc/callback { code }
        SSO->>SSO: Exchange code for tokens
        SSO->>DB: UPSERT user (from OIDC claims)
        SSO->>JWT: generate_tokens(user_id, roles)
        JWT-->>SSO: { tokens }
        SSO-->>User: Redirect with tokens
    end

    rect rgb(248, 240, 255)
        Note over User,RBAC: Protected Request
        User->>RBAC: Request with Bearer token
        RBAC->>JWT: validate_token(token)
        JWT-->>RBAC: { user_id, roles, tenant_id }
        RBAC->>DB: SELECT permissions FROM rbac_roles WHERE role IN ($roles)
        DB-->>RBAC: permissions[]
        RBAC->>RBAC: Check required_permission in user_permissions
        alt Authorized
            RBAC-->>User: 200 OK
        else Unauthorized
            RBAC-->>User: 403 Forbidden
        end
    end
```

## Roles

| Role | Permissions |
|------|------------|
| `admin` | Full access |
| `manager` | Read + Write + Execute agents |
| `analyst` | Read + Analyze |
| `viewer` | Read only |

## JWT Claims

```json
{
  "sub": "user_id",
  "tenant_id": "tenant_id",
  "roles": ["manager"],
  "permissions": ["boq:read", "boq:write", "agents:execute"],
  "exp": 1234567890
}
```

## Token Refresh Flow

1. Client detects 401 response
2. POST `/auth/refresh` with refresh_token
3. Validate refresh_token against DB (not revoked, not expired)
4. Generate new access_token (15min TTL)
5. Old refresh_token revoked, new one issued
