#!/usr/bin/env bash
set -Eeuo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="$PROJECT_ROOT/backend"
FRONTEND_DIR="$PROJECT_ROOT/frontend"
VENV_DIR="${INSIGHT_VENV_DIR:-/opt/insight-web-venv}"
UNIT_SOURCE="$PROJECT_ROOT/deploy/systemd"
LOCK_FILE="/run/lock/insight-web-deploy.lock"

exec 9>"$LOCK_FILE"
flock -n 9 || { echo "Another InsightPro deployment is running" >&2; exit 1; }

if [[ ! -f "$PROJECT_ROOT/.env" ]]; then
  echo "Missing $PROJECT_ROOT/.env" >&2
  exit 1
fi

if [[ ! -x "$VENV_DIR/bin/python" ]]; then
  python3 -m venv "$VENV_DIR"
fi

"$VENV_DIR/bin/python" -m pip install --upgrade pip
"$VENV_DIR/bin/python" -m pip install -r "$BACKEND_DIR/requirements-dev.txt"
(
  cd "$BACKEND_DIR"
  STARTUP_CATCHUP_ENABLED=false "$VENV_DIR/bin/python" -m pytest -q
)

(
  cd "$FRONTEND_DIR"
  npm ci
  npm run lint
  npm run build
)

install -m 0644 "$UNIT_SOURCE/insight-backend.service" /etc/systemd/system/insight-backend.service
install -m 0644 "$UNIT_SOURCE/insight-frontend.service" /etc/systemd/system/insight-frontend.service
install -m 0644 "$UNIT_SOURCE/insight-web.target" /etc/systemd/system/insight-web.target
install -m 0644 "$UNIT_SOURCE/insight-health-guard.service" /etc/systemd/system/insight-health-guard.service
install -m 0644 "$UNIT_SOURCE/insight-health-guard.timer" /etc/systemd/system/insight-health-guard.timer
systemctl daemon-reload
systemctl enable insight-web.target
systemctl enable --now insight-health-guard.timer
systemctl start insight-web.target
systemctl restart insight-backend.service
systemctl restart insight-frontend.service

for _ in $(seq 1 180); do
  if "$PROJECT_ROOT/scripts/health-check.sh" >/dev/null 2>&1; then
    "$PROJECT_ROOT/scripts/health-check.sh"
    echo "InsightPro deployment completed"
    exit 0
  fi
  sleep 1
done

echo "Deployment health check failed" >&2
systemctl --no-pager --full status insight-backend.service insight-frontend.service >&2 || true
exit 1
