#!/bin/bash
set -e

echo "=== Pre-Deployment Checks ==="
cd backend

echo "1. Running golden tests..."
python -m pytest tests/golden/ -v --tb=short

echo "2. Running integration tests..."
python -m pytest tests/integration/ -v --tb=short

echo "3. Checking test coverage..."
python -m pytest tests/ --cov=app --cov-report=term --cov-fail-under=20

echo "4. Verifying Alembic migrations..."
alembic current
alembic branches

echo "=== All pre-deployment checks passed! ==="
