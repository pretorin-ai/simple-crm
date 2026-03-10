#!/usr/bin/env bash
set -euo pipefail

# Run Alembic migrations before starting the app
echo "Running database migrations..."
alembic upgrade head

# Start uvicorn
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --timeout-graceful-shutdown 30
