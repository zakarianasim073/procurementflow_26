# ProcureFlow API Contract Pack — Overview

**Version**: 2.0 (aligned with FEAP/PFX v2 frontend)  
**Base URL**: `http://localhost:8000/api/v1` (v1) / `http://localhost:8000/api/v2` (v2 enterprise)  
**Authentication**: JWT Bearer token (access + refresh rotation)  
**Content-Type**: `application/json` (request/response), `multipart/form-data` (file uploads)  
**OpenAPI Spec**: `GET /openapi.json` (auto-generated from FastAPI)

---

## Architecture Constraints (ADR-aligned)

| Constraint | ADR Reference | Enforcement |
|---|---|---|
| **AgentBrain is sole orchestrator** | ADR-001 | All multi-step workflows go through `/api/agents/*` or `/api/pipeline/*` |
| **PostgreSQL-only for persistent state** | ADR-005 | No Mongo/Redis primary writes; Redis = cache/L2 only |
| **RLS on every tenant-scoped table** | ADR-020 | `tenant_id` column + `FORCE ROW LEVEL SECURITY` |
| **Works-only filter at scan stage** | AGENTS.md | `category == "Works"` enforced in TenderRadarAgent |
| **Canonical ORM only** | W-001 fix | `app.db.models` frozen; `app.models.*` only |
| **e-GP access via subprocess isolation** | AGENTS.md | `_sub_dl.py` only; no in-process httpx to e-GP |
| **Package_no as canonical FK** | T-029 | All joins use `normalized_package_no` |

---

## Versioning Policy

| Version | Status | Prefix | Breaking Changes |
|---|---|---|---|
| v1 | Stable | `/api/v1/*` | None planned; additive only |
| v2 | Enterprise | `/api/v2/*` | SSO, RBAC, billing, multi-tenant isolation |

- **Header**: `Accept: application/vnd.procureflow.v1+json` (optional, defaults to v1)
- **Deprecation**: 12-month notice via `Sunset` header + changelog

---

## Common Response Envelope

```json
{
  "success": true,
  "data": { ... },
  "meta": {
    "request_id": "uuid",
    "timestamp": "2026-07-21T12:00:00Z",
    "version": "v1.2.3"
  }
}
```

**Error envelope** (RFC 7807 compatible):
```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Human-readable description",
    "details": [{ "field": "email", "issue": "invalid format" }],
    "request_id": "uuid"
  }
}
```

**HTTP status mapping**:
- `200` — OK
- `201` — Created
- `202` — Accepted (async job queued; poll `/jobs/{id}`)
- `400` — Validation error
- `401` — Unauthenticated (token missing/expired)
- `403` — Forbidden (tenant/role mismatch)
- `404` — Not found
- `409` — Conflict (idempotency key reuse, concurrent modification)
- `422` — Unprocessable entity (semantic validation)
- `429` — Rate limited
- `500` — Internal error (logged with `request_id`)
- `503` — Service unavailable (Celery/Redis down)

---

## Authentication & Authorization

| Flow | Endpoint | Token TTL |
|---|---|---|
| Password grant | `POST /api/v1/auth/login` | Access: 15m, Refresh: 30d |
| Refresh rotation | `POST /api/v1/auth/refresh` | New access + new refresh (reuse detection) |
| Logout (revoke family) | `POST /api/v1/auth/logout` | Immediate |
| SSO (v2) | `POST /api/v2/sso/oidc/callback` | Enterprise only |

**Token payload** (JWT, RS256):
```json
{
  "sub": "user-uuid",
  "plan": "FREE|PRO|ENTERPRISE",
  "tenant_id": "tenant-uuid",
  "role": "owner|admin|estimator|compliance|viewer",
  "gpt_quota": 50000,
  "exp": 1234567890
}
```

**Permission model** (v2):
- Workspace-level: `executive:read`, `opportunity:write`, `tender:admin`, `trust:read`, `knowledge:write`, `enterprise:admin`
- Scoped via `require_role()` and `require_permission()` dependencies

---

## Rate Limiting

| Tier | Requests/min | Burst | Scope |
|---|---|---|---|
| Anonymous | 10 | 20 | IP |
| FREE | 60 | 120 | User |
| PRO | 300 | 600 | User |
| ENTERPRISE | 1000 | 2000 | Tenant |

- Headers: `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`
- Exceed → `429` with `Retry-After` seconds

---

## Pagination (Cursor-based for lists > 100 items)

```json
{
  "data": [...],
  "pagination": {
    "cursor": "eyJpZCI6MTIzfQ==",
    "next_cursor": "eyJpZCI6MTI0fQ==",
    "has_more": true,
    "limit": 50,
    "total": 1247
  }
}
```

- Query params: `limit`limit`limit` (1-200, default 50), `cursor` (opaque)
- Offset pagination (`skip`/`offset`) supported for backward compat but deprecated

---

## Idempotency

- **Header**: `Idempotency-Key: <uuid>` (client-generated)
- **Scope**: POST/PUT/PATCH mutating endpoints
- **TTL**: 24 hours (Redis)
- **Response**: Replays original `2xx` with `Idempotency-Replay: true` header

---

## Caching

| Endpoint Pattern | Cache-Control | Invalidation |
|---|---|---|
| `GET /sor/*` | `public, max-age=3600, stale-while-revalidate=86400` | SOR ETL run |
| `GET /search/*` | `private, max-age=60` | Write to index |
| `GET /dashboard/*` | `private, max-age=30` | User action |
| `GET /executive/*` | `private, max-age=300` | Nightly rebuild |
| Mutations | `no-store` | N/A |

- L1: in-process LRU (1000 entries)
- L2: Redis (cluster-aware)
- `ETag`/`If-None-Match` supported on all `GET`

---

## React Query Mapping

```typescript
// Base query client
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,        // 30s
      gcTime: 5 * 60_000,       // 5m
      retry: (count, err) => count < 2 && err.status >= 500,
      refetchOnWindowFocus: false,
    },
  },
});

// Auth-aware fetcher
async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const token = useAuthStore.getState().accessToken;
  const res = await fetch(`${BASE_URL}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
      'Idempotency-Key': options?.method !== 'GET' ? crypto.randomUUID() : undefined,
      ...options?.headers,
    },
  });
  if (!res.ok) throw new ApiError(await res.json(), res.status);
  return res.json();
}
```

**Query keys** (colocated with contract docs):
```typescript
// Example: BOQ comparison
const boqKeys = {
  all: ['boq'] as const,
  lists: () => [...boqKeys.all, 'list'] as const,
  detail: (id: string) => [...boqKeys.all, 'detail', id] as const,
  job: (jobId: string) => [...boqKeys.all, 'job', jobId] as const,
};
```

---

## Zustand Store Contracts

```typescript
// stores/auth.ts
interface AuthState {
  accessToken: string | null;
  refreshToken: string | null;
  user: UserProfile | null;
  login: (email: string, password: string) => Promise<void>;
  refresh: () => Promise<void>;
  logout: () => Promise<void>;
  hasPermission: (key: string) => boolean;
}

// stores/workspace.ts
interface WorkspaceState {
  activeWorkspace: WorkspaceId;
  setWorkspace: (id: WorkspaceId) => void;
  sectionPermissions: Record<string, boolean>;
}
```

---

## WebSocket / Server-Sent Events

| Channel | Path | Auth | Events |
|---|---|---|---|
| Agent job progress | `/api/v1/pipeline/ws/{task_id}` | JWT | `status`, `progress`, `result`, `error` |
| Crawler status | `/api/v1/crawler/ws` | JWT | `plugin_started`, `page_done`, `completed` |
| Notifications | `/api/v1/notifications/ws` | JWT | `alert`, `info`, `task_complete` |

---

## API Module Index (20 Contracts)

| # | Module | Router Prefix | Contract Doc |
|---|---|---|---|
| 00 | Overview | — | `00_API_OVERVIEW.md` |
| 01 | Authentication | `/auth` | `01_AUTH_API.md` |
| 02 | Dashboard | `/dashboard` | `02_DASHBOARD_API.md` |
| 03 | Tender | `/tender`, `/tenders` | `03_TENDER_API.md` |
| 04 | BOQ | `/boq` | `04_BOQ_API.md` |
| 05 | Document AI | `/tender-docs`, `/agents/egp/*` | `05_DOCUMENT_AI_API.md` |
| 06 | SOR | `/sor` | `06_SOR_API.md` |
| 07 | Pricing | `/pricing`, `/rate-analysis` | `07_PRICING_API.md` |
| 08 | Competitor | `/competitors`, `/intel` | `08_COMPETITOR_API.md` |
| 09 | Win Probability | `/executive`, `/ppr2025` | `09_WIN_PROBABILITY_API.md` |
| 10 | Executive | `/executive` | `10_EXECUTIVE_API.md` |
| 11 | Knowledge | `/agents/knowledge/*`, `/knowledge` | `11_KNOWLEDGE_API.md` |
| 12 | AI Agent | `/agents/*`, `/pipeline/*`, `/ollama/*` | `12_AI_AGENT_API.md` |
| 13 | Notification | `/notifications`, `/webhooks` | `13_NOTIFICATION_API.md` |
| 14 | Report | `/reports` | `14_REPORT_API.md` |
| 15 | Admin | `/admin`, `/canonical`, `/system` | `15_ADMIN_API.md` |
| 16 | Audit | `/audit` | `16_AUDIT_API.md` |
| 17 | Search | `/search` | `17_SEARCH_API.md` |
| 18 | Files | `/uploads`, `/storage` | `18_FILES_API.md` |
| 19 | Webhooks | `/webhooks` | `19_WEBHOOKS.md` |

---

## Change Log

| Version | Date | Changes |
|---|---|---|
| 2.0 | 2026-07-21 | Full contract pack aligned with FEAP/PFX v2, AgentBrain v2, v2 enterprise APIs |
| 1.0 | 2026-06-15 | Initial v1 contracts |