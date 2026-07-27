# Authentication API Contract

**Router**: `/api/v1/auth`  
**Tags**: `auth`  
**Auth**: Public (login/register), JWT (refresh/me/change-password)

---

## Endpoint Catalog

| Method | Path | Purpose | Auth |
|--------|------|---------|------|
| POST | `/auth/login` | Email/password login → access + refresh tokens | Public |
| POST | `/auth/register` | Register new user (FREE plan) | Public |
| POST | `/auth/refresh` | Rotate refresh token → new access + refresh | Public (refresh token) |
| POST | `/auth/logout` | Revoke refresh token family | JWT |
| GET | `/auth/me` | Current user profile + quota | JWT |
| POST | `/auth/change-password` | Change password (old + new) | JWT |

---

## Request/Response Schemas

### `POST /auth/login`

**Request**
```json
{
  "email": "user@company.com",
  "password": "securePassword123"
}
```

**Response (200)**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "refresh_token": "rt_abc123...",
  "token_type": "bearer",
  "user": {
    "id": "uuid",
    "email": "user@company.com",
    "plan": "FREE|PRO|ENTERPRISE",
    "tenant_id": "tenant-uuid",
    "role": "viewer|admin|owner",
    "name": "Display Name"
  }
}
```

**Errors**
- `401` Invalid credentials
- `429` Rate limit (5 req/min per IP)

---

### `POST /auth/register`

**Request**
```json
{
  "email": "new@company.com",
  "password": "securePassword123"
}
```

**Response (201)**
```json
{
  "access_token": "...",
  "refresh_token": "...",
  "token_type": "bearer",
  "user": { "id": "...", "email": "...", "plan": "FREE", "tenant_id": "...", "role": "admin", "name": "New" }
}
```

**Errors**
- `409` Email already registered
- `429` Rate limit (3 req/5min per IP)

---

### `POST /auth/refresh`

**Request**
```json
{ "refresh_token": "rt_abc123..." }
```

**Response (200)**
```json
{
  "access_token": "eyJ...",
  "refresh_token": "rt_new...",
  "token_type": "bearer"
}
```

**Behavior**
- Rotates token family (old refresh revoked)
- Reuse detection → entire family revoked (audit logged)
- `401` uniform error (no reason leakage)

---

### `POST /auth/logout`

**Request**
```json
{ "refresh_token": "rt_abc123..." }
```

**Response (200)**
```json
{ "success": true }
```
Idempotent.

---

### `GET /auth/me`

**Response (200)**
```json
{
  "success": true,
  "user": {
    "id": "uuid",
    "email": "user@company.com",
    "name": "Zakaria Nasim",
    "plan": "ENTERPRISE",
    "tenant_id": "tenant-owner-...",
    "role": "owner",
    "is_active": true,
    "gpt_quota_remaining": 498234
  }
}
```

---

### `POST /auth/change-password`

**Request**
```json
{ "old_password": "current123", "new_password": "newSecure456" }
```

**Response (200)**
```json
{ "success": true, "message": "Password changed successfully" }
```

**Errors**
- `400` Missing fields / new password < 8 chars
- `401` Current password incorrect
- `404` User not found

---

## Error Schema (All Endpoints)

```json
{
  "detail": "Human-readable error message",
  "status_code": 401,
  "error_code": "AUTH_INVALID_CREDENTIALS"
}
```

Common `error_code` values:
- `AUTH_INVALID_CREDENTIALS`
- `AUTH_RATE_LIMITED`
- `AUTH_EMAIL_EXISTS`
- `AUTH_TOKEN_EXPIRED`
- `AUTH_TOKEN_REVOKED`
- `AUTH_USER_INACTIVE`

---

## Permission Requirements

| Endpoint | Required Role | Tenant Scope |
|----------|---------------|--------------|
| `/login`, `/register`, `/refresh`, `/logout` | Public | N/A |
| `/me`, `/change-password` | Any authenticated | Own user only |

---

## Rate Limits

| Endpoint | Limit | Window |
|----------|-------|--------|
| `/login` | 5 req | 60 sec |
| `/register` | 3 req | 300 sec |
| `/refresh` | 20 req | 60 sec |
| Others | 60 req | 60 sec |

Headers returned: `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`

---

## Caching

- `GET /me`: `private, max-age=30` (ETag on user version)
- Others: `no-store`

---

## React Query Mapping

```typescript
// hooks/useAuth.ts
export const authKeys = {
  me: ['auth', 'me'] as const,
};

export function useMe() {
  return useQuery({
    queryKey: authKeys.me,
    queryFn: () => apiFetch<MeResponse>('/auth/me'),
    staleTime: 60_000,
  });
}

export function useLogin() {
  return useMutation({
    mutationFn: (cred: LoginRequest) => apiFetch<LoginResponse>('/auth/login', {
      method: 'POST',
      body: JSON.stringify(cred),
    }),
    onSuccess: (data) => {
      queryClient.setQueryData(authKeys.me, { success: true, user: data.user });
      useAuthStore.getState().setTokens(data.access_token, data.refresh_token);
    },
  });
}
```

---

## Zustand Store Updates

```typescript
// stores/auth.ts
interface AuthState {
  accessToken: string | null;
  refreshToken: string | null;
  user: UserProfile | null;
  setTokens: (access: string, refresh: string) => void;
  clear: () => void;
  hasPermission: (key: string) => boolean;
}
```

---

## Versioning

- `v1` (current): JWT + refresh token rotation
- `v2` (planned): OIDC/SAML SSO via `/api/v2/sso/*`

---

## OpenAPI Reference

See `/openapi.json#/paths/~1api~1v1~1auth~1login/post`