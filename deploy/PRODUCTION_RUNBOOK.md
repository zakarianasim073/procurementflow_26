# ProcureFlow Production Runbook

## Deployment contract

- Frontend: `https://procureflowbd.com`
- WWW alias: `https://www.procureflowbd.com`
- API: `https://api.procureflowbd.com`
- Server: `server.procureflowbd.com`
- Repository: `/opt/procureflow/app`
- Protected environment: `/opt/procureflow/secrets/.env.production` (`0600`)
- Public container ports: Nginx `80` and `443` only
- PostgreSQL, PgBouncer, Redis, MinIO, Flower, Prometheus, Grafana,
  Tempo, exporters, FastAPI and Celery remain Docker-network private.

Administrative dashboards are reached only through SSH port forwarding.

## Immutable release preparation

```sh
cd /opt/procureflow/app
git fetch --prune origin codex/procureflow-enterprise
git checkout --detach <full-40-character-reviewed-commit>
python3 scripts/verify_release_clean.py
```

Generate internal secrets once as `procureflow`:

```sh
sh deploy/generate-production-secrets.sh
```

Then edit only the empty operator-supplied fields in the protected file.
Never copy that file into the Git checkout.

## Compose validation

```sh
cd /opt/procureflow/app
COMPOSE="sudo docker compose --env-file /opt/procureflow/secrets/.env.production -f docker-compose.yml -f docker-compose.prod.yml"
$COMPOSE config --quiet
```

Do not print the rendered production configuration because it contains
interpolated runtime secrets.

## Database contract

The database image is PostgreSQL 17 with pgvector available. New empty data
directories create `vector`, `pg_trgm`, and `uuid-ossp`; Alembic owns the
application schema. PgBouncer uses transaction mode for API and worker traffic.
Migrations bypass PgBouncer and connect directly to `postgres:5432`.

Database migration is a separate, explicitly approved action:

```sh
$COMPOSE up -d postgres
$COMPOSE --profile migration run --rm migration
```

## Initial launch order

The host Nginx installed during Phase 2 must be stopped before container Nginx
binds ports 80/443.

```sh
$COMPOSE up -d postgres redis minio minio-init pgbouncer
$COMPOSE up -d backend worker-high worker-default worker-low frontend nginx
curl --fail -H 'Host: api.procureflowbd.com' http://127.0.0.1/api/ready
```

The observability stack is optional at initial launch:

```sh
$COMPOSE --profile observability up -d \
  tempo postgres-exporter node-exporter prometheus grafana flower
```

Use SSH forwarding for dashboards, for example a loopback-only tunnel to the
Grafana container after resolving its internal address. Never publish dashboard
ports in Compose or UFW.

## DNS and TLS gate

Do not request certificates until public A/CNAME records resolve to the VPS.
The active Compose file mounts `deploy/nginx/procureflow.http.conf`, which
serves ACME challenges without referencing nonexistent certificates.

After certificates exist, review
`deploy/nginx/procureflow.https.conf.example`, copy it to a runtime-only
configuration file, validate it inside the Nginx container, then activate it.

## Resource allocation

Initial limits for the 8-vCPU/16-GiB VPS:

| Service | CPU limit | Memory limit |
|---|---:|---:|
| FastAPI, 3 Uvicorn workers | 2 | 2 GiB |
| Celery high, concurrency 2 | 1 | 1 GiB |
| Celery default, concurrency 3 | 2 | 2 GiB |
| Celery low, concurrency 1 | 1 | 1 GiB |
| PostgreSQL | 2 | 4 GiB |
| Redis | 0.5 | 512 MiB |
| MinIO | 1 | 1 GiB |
| PgBouncer | 0.5 | 128 MiB |
| Frontend and edge Nginx | 1 combined | 256 MiB combined |

Monitoring is optional because enabling the complete profile adds roughly
1.4 GiB of configured memory limits. Ollama and local LLM inference remain
disabled on this CPU-only initial host.

## Rollback

Record the prior SHA before deployment. To roll back application containers:

```sh
cd /opt/procureflow/app
git checkout --detach <previous-reviewed-sha>
python3 scripts/verify_release_clean.py
$COMPOSE config --quiet
$COMPOSE build backend worker-high worker-default worker-low frontend
$COMPOSE up -d backend worker-high worker-default worker-low frontend nginx
```

Database rollback is not automatic. Take a verified PostgreSQL backup before
each migration and use a migration-specific recovery plan.
