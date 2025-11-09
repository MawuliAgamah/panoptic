#!/usr/bin/env bash
set -euo pipefail

# Resolve project root (location of this script)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$SCRIPT_DIR"

# Prefer project's virtualenv if present
VENV_BIN="$ROOT_DIR/.venv/bin"
if [[ -x "$VENV_BIN/uvicorn" ]]; then
  UVICORN_CMD="$VENV_BIN/uvicorn"
elif command -v uvicorn >/dev/null 2>&1; then
  UVICORN_CMD="uvicorn"
else
  echo "Error: uvicorn is not installed. Activate your venv or install uvicorn." >&2
  exit 1
fi

# Ensure src is on PYTHONPATH so 'application...' imports resolve
export PYTHONPATH="$ROOT_DIR/src${PYTHONPATH+:$PYTHONPATH}"

# Ensure logs directory exists and point KG_LOG_FILE at it
mkdir -p "$ROOT_DIR/logs"
export KG_LOG_FILE="$ROOT_DIR/logs/app.log"

# Load environment variables from .env if present
if [[ -f "$ROOT_DIR/.env" ]]; then
  # shellcheck disable=SC1090
  set -a
  source "$ROOT_DIR/.env"
  set +a
fi

# Defaults with environment overrides
HOST="${WEB_HOST:-0.0.0.0}"
PORT="${WEB_PORT:-8001}"
RELOAD_FLAG="--reload"
if [[ "${NO_RELOAD:-}" == "1" || "${RELOAD:-true}" == "false" ]]; then
  RELOAD_FLAG=""
fi

echo "Starting FastAPI backend on $HOST:$PORT (reload=$( [[ -n "$RELOAD_FLAG" ]] && echo on || echo off ))"
exec "$UVICORN_CMD" application.api.main:app --host "$HOST" --port "$PORT" $RELOAD_FLAG
