# ProcureFlow Production Runbook

## Services

- Backend API: FastAPI on container port `8000`
- Frontend: Vite/Tailwind static build on container port `80`
- Edge TLS: nginx on host `80` and `443`
- Monitoring: Prometheus on `9090`, Grafana on `3001`
- Database: PostgreSQL 17 on host `5433`
- Queue/cache: Redis on host `6379`

## Required `.env` Values

```env
ENVIRONMENT=production
DATABASE_URL=postgresql+asyncpg://<user>:<url-encoded-password>@postgres:5432/procureflow_bd
PGBOUNCER_URL=postgresql+asyncpg://<user>:<url-encoded-password>@pgbouncer:6432/procureflow_bd
POSTGRES_USER=<database-user>
POSTGRES_PASSWORD=<strong-database-password>
POSTGRES_DB=procureflow_bd
REDIS_URL=redis://redis:6379/0
JWT_SECRET=<strong-random-secret>
JWT_REFRESH_SECRET=<strong-random-refresh-secret>
OWNER_EMAIL=<owner-login-email>
OWNER_PASSWORD=<owner-login-password>
ALLOWED_ORIGINS=https://your-domain.example
FRONTEND_URL=https://your-domain.example
GRAFANA_ADMIN_USER=admin
GRAFANA_ADMIN_PASSWORD=<strong-grafana-password>
MINIO_ROOT_USER=<minio-admin-user>
MINIO_ROOT_PASSWORD=<strong-minio-password>
```

## Start Stack

```powershell
docker compose -f docker-compose.yml -f docker-compose.prod.yml config --quiet
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d postgres redis minio pgbouncer
docker compose -f docker-compose.yml -f docker-compose.prod.yml run --rm backend alembic upgrade head
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d backend worker-high worker-default worker-low frontend tempo postgres-exporter node-exporter prometheus grafana flower
```

## Issue TLS Certificate

Point DNS `A`/`AAAA` records to the server first, then run:

```powershell
.\scripts\init_ssl_certbot.ps1 -Domain your-domain.example -Email admin@your-domain.example
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d nginx certbot
```

For a dry run against Let's Encrypt staging:

```powershell
.\scripts\init_ssl_certbot.ps1 -Domain your-domain.example -Email admin@your-domain.example -Staging
```

## Health Checks

```powershell
curl http://localhost:8000/api/live
curl http://localhost:8000/api/ready
curl http://localhost:8000/metrics
curl http://localhost:9090/-/ready
```

Grafana: `http://localhost:3001`

Prometheus target should show `procureflow-backend` as UP.
