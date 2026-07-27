# ARCH-008: Deployment Architecture

```mermaid
graph TB
    subgraph "Production Environment"
        subgraph "Application Tier"
            FASTAPI[FastAPI App<br/>Python 3.10<br/>Uvicorn Workers<br/>:8000]
            WORKERS[Background Workers<br/>Celery / asyncio]
            FRONTEND[Frontend<br/>React SPA + Nginx<br/>:8080]
        end

        subgraph "Data Tier"
            PG[(PostgreSQL 17<br/>Container: 5432<br/>Host: 5433<br/>procureflow_bd)]
            REDIS[(Redis 7<br/>:6379<br/>AOF persistence)]
            MINIO[(MinIO<br/>:9000/:9001<br/>S3-compatible)]
            PGBOUNCER[PgBouncer<br/>:6432<br/>Transaction pool]
        end

        subgraph "Monitoring"
            PROM[Prometheus<br/>:9090]
            GRAF[Grafana<br/>:3000]
            TEMPO[Tempo<br/>:4317/4318]
        end

        subgraph "External"
            EGP[e-GP Portal<br/>eprocure.gov.bd]
            BD_MKT[BD Market Sites<br/>Material Prices]
        end
    end

    BROWSER -->|HTTPS :443| FRONTEND
    FRONTEND -->|HTTP :8000| FASTAPI
    FASTAPI --> PGBOUNCER
    PGBOUNCER --> PG
    FASTAPI --> REDIS
    FASTAPI --> MINIO
    WORKERS --> PGBOUNCER
    WORKERS --> REDIS
    WORKERS --> EGP
    WORKERS --> BD_MKT
    FASTAPI -.->|OTLP| TEMPO
    PROM -.->|scrape :8000/metrics| FASTAPI
    GRAF -.->|query| PROM

    style PG fill:#336791,color:#fff
    style REDIS fill:#DC382D,color:#fff
    style FASTAPI fill:#009688,color:#fff
```

## Deployment Stack

| Component | Technology | Container Port | Host Port | Notes |
|-----------|-----------|---------------|-----------|-------|
| Runtime | Python 3.10 | — | 8000 | Uvicorn ASGI server |
| Web Server | Uvicorn | 8000 | 8000 | `--host 0.0.0.0 --port 8000` |
| Database | PostgreSQL 17 | **5432** | **5433** | Host port 5433 avoids collision with local PG |
| Cache | Redis 7 | 6379 | 6379 | AOF persistence enabled |
| Storage | MinIO | 9000 | 9000 | S3-compatible object storage |
| Frontend | React SPA (Nginx) | 80 | 8080 | Static build served by Nginx |
| Pooler | PgBouncer | 6432 | 6432 | Transaction-mode connection pooling |
| Monitoring | Prometheus | 9090 | 9090 | Metrics scraping |
| Dashboard | Grafana | 3000 | 3000 | Dashboards + alerting |
| Tracing | Tempo | 4317/4318 | 4317/4318 | OTLP gRPC + HTTP |

### Port Mapping Explainer

PostgreSQL inside the Docker container listens on the default port **5432**. All container-internal services connect via `postgres:5432`. The host-side port is mapped to **5433** to avoid collision with any PostgreSQL instance running on the developer's machine. The `DATABASE_URL` uses `:5432` when connecting container-to-container, and `:5433` only when connecting from the host (local dev, `psql`, pgAdmin).

## Startup Sequence

1. Load SOR data from CSV/DB into memory
2. Include core v1 routers (synchronous)
3. Start background thread for remaining routers
4. Initialize RBAC permissions and system roles
5. Initialize Redis + per-tenant rate limiter
6. Start AgentBrain + AgentRegistry (49 agents)
7. Configure OpenTelemetry/Prometheus
8. Mount SPA catch-all for frontend

## Health Check

```
GET /api/system/health
{
  "status": "healthy",
  "database": "connected",
  "redis": "connected",
  "agents": 49,
  "sor_rates": 4545
}
```
