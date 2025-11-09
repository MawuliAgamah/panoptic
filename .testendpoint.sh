#!/usr/bin/env bash
set -euo pipefail

# Test the CSV upload endpoint: /api/documents/upload-csv
# Usage:
#   ./.testendpoint.sh [path/to/file.csv]
# Env overrides: WEB_HOST (default 127.0.0.1), WEB_PORT (default 8001),
#                DOMAIN (default "general"), TAGS (default "[]"), DOCUMENT_ID

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$SCRIPT_DIR"

# Load .env if available
if [[ -f "$ROOT_DIR/.env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "$ROOT_DIR/.env"
  set +a
fi

HOST="${WEB_HOST:-127.0.0.1}"
PORT="${WEB_PORT:-8001}"
DOMAIN="${DOMAIN:-general}"
TAGS="${TAGS:-[]}" # Must be a JSON string

# Determine CSV path
CSV_PATH="${1:-}"
if [[ -z "$CSV_PATH" ]]; then
  # Default to a repo sample CSV if none provided
  CSV_PATH="/Users/mawuliagamah/Datasets/NBA Shots Data/NBA_2024_Shots.csv"
fi

if [[ ! -f "$CSV_PATH" ]]; then
  echo "Error: CSV file not found: $CSV_PATH" >&2
  echo "Try one of the repo samples (pass the path as arg):" >&2
  rg -n --files "$ROOT_DIR/src/knowledge_graph/agent/testdata" | rg '\\.csv$' || true
  exit 1
fi

# Generate a document id if not provided
if [[ -z "${DOCUMENT_ID:-}" ]]; then
  if command -v uuidgen >/dev/null 2>&1; then
    DOCUMENT_ID="doc_$(uuidgen | tr 'A-Z' 'a-z' | tr -d '-')"
  else
    DOCUMENT_ID="doc_$(date +%s%3N)"
  fi
fi

URL="http://$HOST:$PORT/api/documents/upload-csv"

echo "Uploading CSV to: $URL"
echo " - file: $CSV_PATH"
echo " - document_id: $DOCUMENT_ID"
echo " - domain: $DOMAIN"
echo " - tags: $TAGS"

set -x
HTTP_STATUS=$(curl -sS -o /tmp/upload_response.json -w "%{http_code}" \
  -X POST "$URL" \
  -F "file=@${CSV_PATH};type=text/csv" \
  -F "document_id=${DOCUMENT_ID}" \
  -F "domain=${DOMAIN}" \
  -F "tags=${TAGS}")
set +x

echo "HTTP $HTTP_STATUS"
if command -v jq >/dev/null 2>&1; then
  jq . </tmp/upload_response.json || cat </tmp/upload_response.json
else
  cat </tmp/upload_response.json
fi

