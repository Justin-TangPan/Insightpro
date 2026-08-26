#!/usr/bin/env bash
set -Eeuo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HEALTH_CHECK="$PROJECT_ROOT/scripts/health-check.sh"
LOCK_FILE="/run/lock/insight-web-docker-health-guard.lock"
REPAIR_STAMP="/run/insight-web-docker-health-guard.last-repair"
REPAIR_COOLDOWN_SECONDS="${INSIGHT_REPAIR_COOLDOWN_SECONDS:-3600}"

compose() {
  docker-compose --project-name insight-web --file "$PROJECT_ROOT/compose.yaml" "$@"
}

exec 9>"$LOCK_FILE"
flock -n 9 || exit 0

log() {
  logger -t insight-docker-health-guard -- "$*"
  echo "$*"
}

wait_for_health() {
  local mode="$1" attempts="$2" delay="$3"
  local i
  for i in $(seq 1 "$attempts"); do
    if "$HEALTH_CHECK" "$mode" >/dev/null 2>&1; then
      return 0
    fi
    sleep "$delay"
  done
  return 1
}

notify_failure() {
  local message="$1"
  log "CRITICAL: $message"
  if [[ -n "${INSIGHT_ALERT_WEBHOOK:-}" ]]; then
    local payload
    payload="$(python3 -c 'import json,sys; print(json.dumps({"text": sys.argv[1]}, ensure_ascii=False))' "$message")"
    curl --silent --show-error --max-time 10 \
      -H 'Content-Type: application/json' --data "$payload" \
      "$INSIGHT_ALERT_WEBHOOK" >/dev/null || true
  fi
}

if "$HEALTH_CHECK" full >/dev/null 2>&1; then
  exit 0
fi

log "container data path failed; starting automatic recovery"
if ! "$HEALTH_CHECK" infra >/dev/null 2>&1; then
  # Stale network or container state: clean up and recreate from scratch
  compose down --remove-orphans 2>/dev/null || true
  compose up --detach --remove-orphans
  if ! wait_for_health infra 30 2; then
    compose restart backend frontend || true
    if ! wait_for_health infra 30 2; then
      notify_failure "InsightPro containers did not recover"
      exit 1
    fi
  fi
  if "$HEALTH_CHECK" full >/dev/null 2>&1; then
    log "container recovery restored the complete data path"
    exit 0
  fi
fi

now="$(date +%s)"
last_repair=0
if [[ -f "$REPAIR_STAMP" ]]; then
  last_repair="$(stat -c %Y "$REPAIR_STAMP" 2>/dev/null || echo 0)"
fi

if (( now - last_repair >= REPAIR_COOLDOWN_SECONDS )); then
  touch "$REPAIR_STAMP"
  log "running idempotent freshness repair inside backend container"
  compose exec --no-TTY backend python maintenance.py repair-freshness || true
fi

if wait_for_health full 60 5; then
  log "container data recovery succeeded"
  exit 0
fi

notify_failure "InsightPro container stack remains unhealthy; inspect docker-compose ps and logs"
exit 1
