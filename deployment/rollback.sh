#!/bin/bash
set -e

ENVIRONMENT="${ENVIRONMENT:-staging}"
BACKUP_DIR="/var/www/procureflow/$ENVIRONMENT/backups"
TARGET="/var/www/procureflow/$ENVIRONMENT"

if [[ ! -d "$BACKUP_DIR" ]]; then
  echo "No backup directory found at $BACKUP_DIR"
  exit 1
fi

LATEST=$(ls -t "$BACKUP_DIR" | head -1)
if [[ -z "$LATEST" ]]; then
  echo "No backups found"
  exit 1
fi

echo "Rolling back $ENVIRONMENT to $LATEST..."
cp -r "$BACKUP_DIR/$LATEST"/* "$TARGET/"
echo "Rollback complete."
