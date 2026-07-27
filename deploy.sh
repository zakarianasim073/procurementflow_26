#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ENV_FILE="$SCRIPT_DIR/.env.production"

echo "=== ProcureFlow Phase 1 Deployment ==="
echo ""

if [ ! -f "$ENV_FILE" ]; then
    echo "ERROR: $ENV_FILE not found. Copy .env.example and fill in production values."
    exit 1
fi

export $(grep -v '^#' "$ENV_FILE" | xargs)

echo "Building Docker images..."
docker compose build --no-cache backend

echo "Starting services..."
docker compose up -d postgres redis minio

echo "Waiting for PostgreSQL to be ready..."
until docker compose exec -T postgres pg_isready -U postgres; do
    sleep 1
done

echo "Running database migrations..."
docker compose exec -T backend alembic upgrade head

echo "Starting remaining services..."
docker compose up -d backend nginx grafana prometheus

echo "Waiting for backend to be healthy..."
sleep 5
until curl -sf http://localhost:8000/api/health > /dev/null 2>&1; do
    sleep 2
done

echo ""
echo "=== Deployment Complete ==="
echo "Backend:  http://localhost:8000"
echo "Frontend: http://localhost:3000 (nginx)"
echo "API Health: http://localhost:8000/api/health"
echo "Grafana:  http://localhost:3000"
echo ""
echo "View logs: docker compose logs -f backend"
echo "Stop:      docker compose down"
