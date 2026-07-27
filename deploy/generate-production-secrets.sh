#!/bin/sh
set -eu

target_dir=/opt/procureflow/secrets
target_file="$target_dir/.env.production"

if [ "$(id -un)" != "procureflow" ]; then
  echo "Run this script as the procureflow user." >&2
  exit 1
fi

if [ -e "$target_file" ]; then
  echo "Refusing to overwrite existing production secrets: $target_file" >&2
  exit 1
fi

umask 077
install -d -m 0700 "$target_dir"
temporary_file=$(mktemp "$target_dir/.env.production.tmp.XXXXXX")
trap 'rm -f "$temporary_file"' EXIT HUP INT TERM

postgres_password=$(openssl rand -hex 32)
redis_password=$(openssl rand -hex 32)
minio_password=$(openssl rand -hex 32)
jwt_secret=$(openssl rand -hex 48)
jwt_refresh_secret=$(openssl rand -hex 48)
system_user_password=$(openssl rand -hex 32)
owner_password=$(openssl rand -hex 32)
grafana_password=$(openssl rand -hex 32)

cat >"$temporary_file" <<EOF
PRODUCTION_ENV_FILE=/opt/procureflow/secrets/.env.production
POSTGRES_USER=postgres
POSTGRES_PASSWORD=$postgres_password
POSTGRES_DB=procureflow_bd
DATABASE_URL=postgresql+asyncpg://postgres:$postgres_password@postgres:5432/procureflow_bd
PGBOUNCER_URL=postgresql+asyncpg://postgres:$postgres_password@pgbouncer:6432/procureflow_bd
REDIS_PASSWORD=$redis_password
REDIS_URL=redis://:$redis_password@redis:6379/0
MINIO_ROOT_USER=procureflowadmin
MINIO_ROOT_PASSWORD=$minio_password
MINIO_ACCESS_KEY=procureflowadmin
MINIO_SECRET_KEY=$minio_password
MINIO_ENDPOINT=minio:9000
MINIO_BUCKET=procurementflow-tenders
MINIO_SECURE=false
STORAGE_BACKEND=minio
JWT_SECRET=$jwt_secret
JWT_REFRESH_SECRET=$jwt_refresh_secret
SYSTEM_USER_PASSWORD=$system_user_password
OWNER_EMAIL=
OWNER_PASSWORD=$owner_password
GRAFANA_ADMIN_USER=admin
GRAFANA_ADMIN_PASSWORD=$grafana_password
ENVIRONMENT=production
API_WORKERS=3
ALLOWED_ORIGINS=["https://procureflowbd.com","https://www.procureflowbd.com"]
FRONTEND_URL=https://procureflowbd.com
REQUIRE_API_AUTH=true
RLS_STRICT_CONTEXT=true
MAX_UPLOAD_SIZE_MB=50
OTEL_ENABLED=false
OTEL_EXPORTER_OTLP_ENDPOINT=
OLLAMA_ENABLED=false
OLLAMA_BASE_URL=
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
EGP_EMAIL=
EGP_PASSWORD=
SMTP_HOST=
SMTP_PORT=587
SMTP_USERNAME=
SMTP_PASSWORD=
SMTP_FROM=
SENTRY_DSN=
EOF

chmod 0600 "$temporary_file"
mv "$temporary_file" "$target_file"
trap - EXIT HUP INT TERM
echo "Created protected production environment file at $target_file"
echo "External provider credentials and OWNER_EMAIL still require operator input."
