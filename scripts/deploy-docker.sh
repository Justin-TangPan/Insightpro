#!/usr/bin/env bash
set -Eeuo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export DOCKER_API_VERSION="${DOCKER_API_VERSION:-1.39}"
VENV_DIR="${INSIGHT_VENV_DIR:-/opt/insight-web-venv}"
LOCK_FILE="/run/lock/insight-web-docker-deploy.lock"
SWITCHED=false

compose() {
  docker-compose --project-name insight-web --file "$PROJECT_ROOT/compose.yaml" "$@"
}

rollback() {
  local exit_code=$?
  if [[ "$SWITCHED" == "true" ]]; then
    echo "Docker deployment failed; restoring systemd deployment" >&2
    compose down || true
    systemctl disable --now insight-docker-health-guard.timer || true
    systemctl enable --now insight-web.target insight-health-guard.timer || true
  fi
  exit "$exit_code"
}
trap rollback ERR

exec 9>"$LOCK_FILE"
flock -n 9 || { echo "Another InsightPro Docker deployment is running" >&2; exit 1; }

command -v docker-compose >/dev/null || {
  echo "docker-compose is missing; run sudo ./scripts/install-docker-compose.sh" >&2
  exit 1
}
docker info >/dev/null
compose config >/dev/null

(
  cd "$PROJECT_ROOT/backend"
  STARTUP_CATCHUP_ENABLED=false "$VENV_DIR/bin/python" -m pytest -q
)
(
  cd "$PROJECT_ROOT/frontend"
  npm run lint
)

compose build

install -m 0644 "$PROJECT_ROOT/deploy/systemd/insight-docker-health-guard.service" /etc/systemd/system/
install -m 0644 "$PROJECT_ROOT/deploy/systemd/insight-docker-health-guard.timer" /etc/systemd/system/
systemctl daemon-reload

systemctl disable --now insight-health-guard.timer || true
systemctl disable --now insight-web.target || true
SWITCHED=true

compose up --detach --remove-orphans

for _ in $(seq 1 180); do
  if "$PROJECT_ROOT/scripts/health-check.sh" full >/dev/null 2>&1; then
    "$PROJECT_ROOT/scripts/health-check.sh" full
    systemctl enable --now insight-docker-health-guard.timer
    SWITCHED=false
    echo "InsightPro Docker deployment completed"
    exit 0
  fi
  sleep 1
done

compose ps >&2 || true
compose logs --tail 100 >&2 || true
echo "Docker deployment health check failed" >&2
exit 1
