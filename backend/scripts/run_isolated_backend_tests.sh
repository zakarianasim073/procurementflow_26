#!/usr/bin/env bash
set -Eeuo pipefail

SOURCE_DIR="${1:-$(cd "$(dirname "$0")/.." && pwd)}"
REPORT_DIR="${2:-/tmp/procureflow-test-reports}"
shift $(( $# >= 2 ? 2 : $# ))
PYTEST_TARGETS=("$@")
if [ "${#PYTEST_TARGETS[@]}" -eq 0 ]; then
  PYTEST_TARGETS=(".")
fi
IMAGE="${PROCUREFLOW_TEST_IMAGE:-procureflow-backend:3af01b0}"
RUN_ID="pf-test-$(date +%s)-$$"
NETWORK="${RUN_ID}-net"
POSTGRES="${RUN_ID}-postgres"
REDIS="${RUN_ID}-redis"
DB_PASSWORD="$(openssl rand -hex 24)"
REDIS_PASSWORD="$(openssl rand -hex 24)"

cleanup() {
  docker rm -f "$POSTGRES" "$REDIS" >/dev/null 2>&1 || true
  docker network rm "$NETWORK" >/dev/null 2>&1 || true
}
trap cleanup EXIT

mkdir -p "$REPORT_DIR"
chmod 777 "$REPORT_DIR"
docker network create "$NETWORK" >/dev/null
docker run -d --name "$POSTGRES" --network "$NETWORK" --tmpfs /var/lib/postgresql/data \
  -e POSTGRES_DB=procureflow_test -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD="$DB_PASSWORD" pgvector/pgvector:0.8.0-pg17 >/dev/null
docker run -d --name "$REDIS" --network "$NETWORK" --tmpfs /data \
  redis:7.4.5-alpine redis-server --save "" --appendonly no \
  --requirepass "$REDIS_PASSWORD" >/dev/null

for _ in $(seq 1 60); do
  docker exec "$POSTGRES" pg_isready -U postgres -d procureflow_test >/dev/null 2>&1 \
    && docker exec "$REDIS" redis-cli -a "$REDIS_PASSWORD" ping >/dev/null 2>&1 \
    && break
  sleep 1
done
docker exec "$POSTGRES" pg_isready -U postgres -d procureflow_test >/dev/null
docker exec "$REDIS" redis-cli -a "$REDIS_PASSWORD" ping >/dev/null

docker run --rm --network "$NETWORK" \
  --user 0:0 \
  --mount "type=bind,src=${SOURCE_DIR},dst=/source,readonly" \
  --mount "type=bind,src=${REPORT_DIR},dst=/reports" \
  --tmpfs /testwork:rw,size=2g,mode=1777 \
  -e ENVIRONMENT=test \
  -e ALLOWED_ORIGINS='["http://localhost:5173"]' \
  -e PROCUREFLOW_START_AGENTS_ON_STARTUP=0 \
  -e PROCUREFLOW_SOR_DB_ON_STARTUP=0 \
  -e OTEL_ENABLED=false \
  -e DATABASE_URL="postgresql+asyncpg://postgres:${DB_PASSWORD}@${POSTGRES}:5432/procureflow_test" \
  -e DATABASE_URL_SYNC="postgresql+psycopg2://postgres:${DB_PASSWORD}@${POSTGRES}:5432/procureflow_test" \
  -e REDIS_URL="redis://:${REDIS_PASSWORD}@${REDIS}:6379/0" \
  -e CELERY_BROKER_URL="redis://:${REDIS_PASSWORD}@${REDIS}:6379/1" \
  -e CELERY_RESULT_BACKEND="redis://:${REDIS_PASSWORD}@${REDIS}:6379/2" \
  -e CELERY_TASK_ALWAYS_EAGER=true \
  -e CELERY_TASK_EAGER_PROPAGATES=true \
  -e PYTEST_TARGETS="${PYTEST_TARGETS[*]}" \
  -e OPENAI_API_KEY= -e ANTHROPIC_API_KEY= \
  --entrypoint /bin/sh "$IMAGE" -c '
    cp -a /source /testwork/backend
    chown -R procureflow:procureflow /testwork/backend /reports
    python -m pip install --no-cache-dir -r /testwork/backend/requirements-test.txt >/dev/null
    su -s /bin/sh procureflow -c "
      cd /testwork/backend &&
      alembic upgrade head &&
      alembic upgrade head &&
      alembic current &&
      python -m pytest ${PYTEST_TARGETS[*]} --junitxml=/reports/backend-junit.xml -ra
    "
  '
