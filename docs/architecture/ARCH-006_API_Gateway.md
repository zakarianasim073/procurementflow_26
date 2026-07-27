# ARCH-006: API Gateway & Routing

```mermaid
graph TB
    subgraph "Client"
        SPA[React SPA]
        EXT[External Clients]
    end

    subgraph "FastAPI App (port 8000)"
        subgraph "Middleware Pipeline"
            CORS[CORS Middleware]
            RL[Rate Limiter<br/>per-tenant]
            UV[Upload Validator]
            QE[Quota Enforcer]
            EC[Enterprise Context<br/>Auth + Tenant + Audit]
        end

        subgraph "Route Groups"
            V1C[V1 Core<br/>Loaded at startup]
            V1D[V1 Deferred<br/>Loaded async]
            V2[V2 Routes<br/>Loaded async]
            BRAIN_R[Brain Router]
        end

        subgraph "Auth Layer"
            JWT[JWT Validation]
            SSO_S[SAML/OIDC SSO]
            RBAC_S[RBAC Check]
        end
    end

    subgraph "Dependencies"
        DEP_USER[get_current_user<br/>Optional JWT]
        DEP_TENANT[get_tenant_context<br/>from JWT]
        DEP_QUOTA[check_quota<br/>per subscription]
    end

    SPA --> SPA_CATCH[SPA Catch-All]
    EXT --> API_R[API Routes]
    SPA_CATCH --> SPA_INDEX[index.html]

    SPA --> CORS
    EXT --> CORS
    CORS --> RL
    RL --> UV
    UV --> QE
    QE --> EC

    EC --> JWT
    JWT --> SSO_S
    SSO_S --> RBAC_S

    RBAC_S --> V1C
    RBAC_S --> V1D
    RBAC_S --> V2
    RBAC_S --> BRAIN_R

    V1C --> DEP_USER
    V1C --> DEP_TENANT
    V1C --> DEP_QUOTA
```

## Route Loading Strategy

| Group | Load Timing | Routers |
|-------|------------|---------|
| V1 Core | At startup (synchronous) | auth, boq, sor, competitors, pricing, contractors, search, validation, reports |
| V1 Deferred | Background thread | tenders, awards, dashboard, intelligence, predictions, executive, ppr2025, agents, and 20+ more |
| V2 | Background thread | enterprise, sso, analytics, benchmarking, predictions, market_trends, documents, team |
| Brain | At startup | brain_router (orchestration, knowledge, pipeline) |

## Rate Limiting

| Tier | Limit | Window |
|------|-------|--------|
| Free | 60 req/min | Sliding window |
| Pro | 300 req/min | Sliding window |
| Enterprise | Custom | Configurable |

## Error Response Format

```json
{
  "error": "quota_exceeded",
  "message": "Monthly quota exceeded",
  "details": { "used": 1000, "limit": 1000 },
  "retry_after": 2592000
}
```
