#!/bin/bash
set -e

ENVIRONMENT="${ENVIRONMENT:-staging}"
echo "Deploying to $ENVIRONMENT environment..."

if [[ -z "$ENVIRONMENT" ]]; then
  echo "ENVIRONMENT not set. Use 'staging' or 'production'."
  exit 1
fi

# Build frontend
echo "Building frontend..."
cd frontend_v2
npm ci
npm run build
cd ..

# Deploy via rsync or scp
DEPLOY_TARGET="/var/www/procureflow/$ENVIRONMENT"

echo "Syncing to $DEPLOY_TARGET..."
rsync -avz --delete frontend_v2/dist/ "$DEPLOY_TARGET/"

echo "Health check..."
curl -f "https://$ENVIRONMENT.app.procureflow.com/api/health" && echo " OK"

echo "Deployment to $ENVIRONMENT complete."
