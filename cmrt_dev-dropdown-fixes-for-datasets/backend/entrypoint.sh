#!/usr/bin/env bash
set -euo pipefail

# Optional: log helper
log() { echo "[$(date -u +'%Y-%m-%dT%H:%M:%SZ')] $*"; }

# Default app host/port
: "${APP_HOST:=0.0.0.0}"
: "${APP_PORT:=8080}"
: "${APP_MODULE:=main:app}"  # e.g., change if your app module isn't main.py

# Always run Alembic migrations before starting the app
log "Checking and upgrading Alembic migrations..."
alembic upgrade heads
log "Alembic migrations complete."

if [[ "${DATA_MIGRATION:-}" == "true" ]]; then
  log "DATA_MIGRATION=true → running SQL migration script"
  # Allow overriding SQL_FILE via ENV; default location shown below
  : "${ADMIN_SQL:=/app/sql/admin.sql}"
  : "${SCHEMA_SQL:=/app/sql/schema.sql}"
  if [[ ! -f "$ADMIN_SQL" ]]; then
    log "ERROR: SQL file not found at $ADMIN_SQL"
    exit 1
  fi

  if [[ ! -f "$SCHEMA_SQL" ]]; then
    log "ERROR: SQL file not found at $SCHEMA_SQL"
    exit 1
  fi

  if [[ -z "${DATABASE_URL:-}" ]]; then
    log "ERROR: DATABASE_URL is not set"
    exit 1
  fi

  # Execute the SQL file
  python /app/tools/run_sql_file.py --admin-sql "$ADMIN_SQL" --schema-sql "$SCHEMA_SQL" --force --echo
  log "SQL migration completed successfully."
else
  log "DATA_MIGRATION not true → starting FastAPI app"
  # exec uvicorn "$APP_MODULE" --host "$APP_HOST" --port "$APP_PORT" --proxy-headers
  exec uvicorn "$APP_MODULE" --host "$APP_HOST" --port "$APP_PORT"
fi
