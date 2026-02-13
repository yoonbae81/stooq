#!/bin/bash
set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"
SERVICE_NAME="stooq-downloader"

echo "Starting deployment for $SERVICE_NAME..."

# 1. Pull latest code
echo "Pulling latest changes from git..."
if git rev-parse --is-inside-work-tree > /dev/null 2>&1; then
    git pull origin main
else
    echo "Warning: Not a git repository, skipping git pull"
fi

# 2. Update dependencies
if [ -f "$PROJECT_DIR/requirements.txt" ]; then
    echo "Updating dependencies..."
    "$PROJECT_DIR/.venv/bin/pip" install -r "$PROJECT_DIR/requirements.txt"
fi

# 3. Restart services
echo "Restarting service timer..."
if command -v systemctl &> /dev/null && [ "$(uname)" == "Linux" ]; then
    systemctl --user restart "$SERVICE_NAME.timer"
else
    echo "Warning: systemctl not found or not Linux, skipping restart"
fi

echo "Deployment completed successfully!"
