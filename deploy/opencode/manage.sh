#!/usr/bin/env bash
set -Eeuo pipefail

DEPLOY_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$DEPLOY_DIR/../.." && pwd)"
ENV_FILE="/etc/insight-opencode/opencode.env"
export DOCKER_API_VERSION="${DOCKER_API_VERSION:-1.39}"

load_env() {
  [[ -f "$ENV_FILE" ]] || { echo "Missing $ENV_FILE" >&2; exit 1; }
  set -a
  # shellcheck disable=SC1090
  source "$ENV_FILE"
  set +a
  : "${OPENCODE_SERVER_USERNAME:?missing OPENCODE_SERVER_USERNAME}"
  : "${OPENCODE_SERVER_PASSWORD:?missing OPENCODE_SERVER_PASSWORD}"
  : "${OPENCODE_PROVIDER_BASE_URL:?missing OPENCODE_PROVIDER_BASE_URL}"
  : "${OPENCODE_PROVIDER_API_KEY:?missing OPENCODE_PROVIDER_API_KEY}"
  OPENCODE_DATA_ROOT="${OPENCODE_DATA_ROOT:-/var/lib/insight-opencode}"
  OPENCODE_PORT="${OPENCODE_PORT:-4096}"
  OPENCODE_DISK_BUDGET_MB="${OPENCODE_DISK_BUDGET_MB:-20480}"
}

compose() {
  docker-compose --project-name insight-opencode --file "$DEPLOY_DIR/compose.yaml" "$@"
}

bootstrap() {
  load_env
  install -d -m 0750 /etc/insight-opencode
  install -d -m 0750 \
    "$OPENCODE_DATA_ROOT/data" \
    "$OPENCODE_DATA_ROOT/config" \
    "$OPENCODE_DATA_ROOT/cache" \
    "$OPENCODE_DATA_ROOT/state" \
    "$OPENCODE_DATA_ROOT/workspace"

  if [[ ! -f "$OPENCODE_DATA_ROOT/config/opencode.json" ]]; then
    install -m 0640 "$DEPLOY_DIR/opencode.json" "$OPENCODE_DATA_ROOT/config/opencode.json"
  fi

  if [[ ! -d "$OPENCODE_DATA_ROOT/workspace/.git" ]]; then
    rmdir "$OPENCODE_DATA_ROOT/workspace"
    git clone --no-hardlinks "$PROJECT_ROOT" "$OPENCODE_DATA_ROOT/workspace"
    git -C "$OPENCODE_DATA_ROOT/workspace" remote set-url origin "$(git -C "$PROJECT_ROOT" remote get-url origin)"
  fi

  if find "$OPENCODE_DATA_ROOT/workspace" -path '*/.git' -prune -o -type f -name '.env' -print -quit | grep -q .; then
    echo "Refusing to start: workspace contains a .env file" >&2
    exit 1
  fi

  chown -R 10002:10002 "$OPENCODE_DATA_ROOT"
  chmod 0750 "$OPENCODE_DATA_ROOT" "$OPENCODE_DATA_ROOT"/*
  chmod 0640 "$OPENCODE_DATA_ROOT/config/opencode.json"
}

health() {
  load_env
  local response used_mb
  response="$(curl --fail --silent --show-error --max-time 10 \
    --user "$OPENCODE_SERVER_USERNAME:$OPENCODE_SERVER_PASSWORD" \
    "http://127.0.0.1:$OPENCODE_PORT/global/health")"
  python3 -c 'import json,sys; data=json.loads(sys.argv[1]); assert data.get("healthy") is True, data; print("OpenCode", data.get("version", "unknown"), "is healthy")' "$response"
  [[ "$(docker inspect insight-opencode --format '{{.State.Health.Status}}')" == "healthy" ]]
  used_mb="$(du -sm "$OPENCODE_DATA_ROOT" | awk '{print $1}')"
  if (( used_mb > OPENCODE_DISK_BUDGET_MB )); then
    echo "OpenCode persistent data exceeds budget: ${used_mb} MiB > ${OPENCODE_DISK_BUDGET_MB} MiB" >&2
    exit 1
  fi
  echo "Persistent data: ${used_mb} MiB / ${OPENCODE_DISK_BUDGET_MB} MiB budget"
}

case "${1:-}" in
  bootstrap)
    bootstrap
    ;;
  start)
    bootstrap
    compose up --detach --build --remove-orphans
    ;;
  stop)
    load_env
    compose down
    ;;
  restart)
    load_env
    compose restart opencode
    ;;
  upgrade)
    bootstrap
    compose build --pull
    compose up --detach --remove-orphans
    ;;
  health)
    health
    ;;
  status)
    load_env
    compose ps
    ;;
  logs)
    load_env
    compose logs --tail 200 --follow opencode
    ;;
  *)
    echo "Usage: $0 {bootstrap|start|stop|restart|upgrade|health|status|logs}" >&2
    exit 2
    ;;
esac
