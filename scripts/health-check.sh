#!/usr/bin/env bash
set -euo pipefail

MODE="${1:-full}"
if [[ -n "${INSIGHT_PYTHON:-}" ]]; then
  PYTHON_BIN="$INSIGHT_PYTHON"
elif [[ -x /opt/insight-web-venv/bin/python ]]; then
  PYTHON_BIN=/opt/insight-web-venv/bin/python
else
  PYTHON_BIN=python3
fi

if [[ "$MODE" != "infra" && "$MODE" != "full" ]]; then
  echo "Usage: $0 [infra|full]" >&2
  exit 2
fi

fetch() {
  curl --fail --silent --show-error --max-time 10 "$1"
}

validate_status() {
  local expected="$1"
  "$PYTHON_BIN" -c 'import json,sys; data=json.load(sys.stdin); expected=sys.argv[1]; assert data.get("status") == expected, data' "$expected"
}

validate_evaluation() {
  "$PYTHON_BIN" -c 'import json,sys; data=json.load(sys.stdin); items=data.get("items") or []; assert data.get("count", 0) > 0 and len(items) > 0, data; assert all(item.get("repo_name") and item.get("level") for item in items), "incomplete evaluation rows"'
}

# Infrastructure: both processes answer and the browser-facing same-origin
# proxy can reach the backend. This catches bind, process and rewrite failures.
fetch http://127.0.0.1:8000/api/system/health/live | validate_status alive
fetch http://127.0.0.1:3000/ >/dev/null
fetch http://127.0.0.1:3000/api/system/health/live | validate_status alive

if [[ "$MODE" == "infra" ]]; then
  echo "InsightPro infrastructure is healthy"
  exit 0
fi

# Full readiness: database connectivity, all freshness SLAs, non-empty current
# technical data, and the exact evaluation contract consumed by the page.
fetch http://127.0.0.1:8000/api/system/health/ready | validate_status healthy
fetch http://127.0.0.1:3000/api/system/health/ready | validate_status healthy
fetch http://127.0.0.1:3000/api/github-trending/business-eval | validate_evaluation

echo "InsightPro end-to-end data path is healthy"
