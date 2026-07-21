#!/usr/bin/env bash
set -Eeuo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HEALTH_CHECK="$PROJECT_ROOT/scripts/health-check.sh"
PYTHON_BIN="${INSIGHT_PYTHON:-/opt/insight-web-venv/bin/python}"
LOCK_FILE="/run/lock/insight-web-health-guard.lock"
REPAIR_STAMP="/run/insight-web-health-guard.last-repair"
REPAIR_COOLDOWN_SECONDS="${INSIGHT_REPAIR_COOLDOWN_SECONDS:-3600}"

exec 9>"$LOCK_FILE"
flock -n 9 || exit 0

log() {
  logger -t insight-health-guard -- "$*"
  echo "$*"
}

wait_for_health() {
  local mode="$1"
  local attempts="$2"
  local delay="$3"
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
    payload="$($PYTHON_BIN -c 'import json,sys; print(json.dumps({"text": sys.argv[1]}, ensure_ascii=False))' "$message")"
    curl --silent --show-error --max-time 10 \
      -H 'Content-Type: application/json' \
      --data "$payload" \
      "$INSIGHT_ALERT_WEBHOOK" >/dev/null || true
  fi
}

if "$HEALTH_CHECK" full >/dev/null 2>&1; then
  log "end-to-end health check passed"
  exit 0
fi

log "health check failed; starting automatic recovery"

# Process/proxy failures are repaired by systemd. Data failures do not cause a
# restart loop; they enter the idempotent catch-up path below.
if ! "$HEALTH_CHECK" infra >/dev/null 2>&1; then
  log "infrastructure path failed; restarting InsightPro target"
  systemctl restart insight-web.target
  if ! wait_for_health infra 30 2; then
    notify_failure "InsightPro infrastructure did not recover after restart"
    exit 1
  fi
  if "$HEALTH_CHECK" full >/dev/null 2>&1; then
    log "automatic infrastructure recovery restored the complete data path"
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
  log "data readiness failed; running idempotent freshness repair"
  (
    cd "$PROJECT_ROOT/backend"
    STARTUP_CATCHUP_ENABLED=false "$PYTHON_BIN" maintenance.py repair-freshness
  ) || true
else
  log "freshness repair is in cooldown; checking whether the previous repair completed"
fi

if wait_for_health full 60 5; then
  log "automatic recovery succeeded"
  exit 0
fi

notify_failure "InsightPro remains unhealthy after automatic recovery; inspect systemctl status and journalctl -u insight-health-guard.service"
exit 1
