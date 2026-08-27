#!/usr/bin/env bash
set -Eeuo pipefail

DEPLOY_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$DEPLOY_DIR/../.." && pwd)"
ENV_FILE="/etc/insight-opencode/opencode.env"

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
  OPENCODE_MAX_ACTIVE="${OPENCODE_MAX_ACTIVE:-6}"
  OPENCODE_IDLE_SECONDS="${OPENCODE_IDLE_SECONDS:-1800}"
  if [[ -f /etc/insight-opencode/gateway.secret ]]; then
    OPENCODE_GATEWAY_SECRET="$(</etc/insight-opencode/gateway.secret)"
    export OPENCODE_GATEWAY_SECRET
  fi
}

compose() {
  docker-compose --project-name insight-opencode --file "$DEPLOY_DIR/compose.yaml" "$@"
}

bootstrap() {
  load_env
  install -d -m 0750 /etc/insight-opencode
  if [[ ! -f /etc/insight-opencode/gateway.secret ]]; then
    local gateway_secret="$(openssl rand -hex 32)"
    printf '%s' "$gateway_secret" | install -m 0600 /dev/stdin /etc/insight-opencode/gateway.secret
  fi
  install -o 10001 -g 10001 -m 0400 /etc/insight-opencode/gateway.secret /etc/insight-opencode/backend-gateway.secret
  load_env
  install -d -m 0750 \
    "$OPENCODE_DATA_ROOT/spaces" \
    "$OPENCODE_DATA_ROOT/knowledge"

  if [[ ! -d "$OPENCODE_DATA_ROOT/template/.git" ]]; then
    git clone --no-hardlinks "$PROJECT_ROOT" "$OPENCODE_DATA_ROOT/template"
    git -C "$OPENCODE_DATA_ROOT/template" remote set-url origin "$(git -C "$PROJECT_ROOT" remote get-url origin)"
  fi

  if find "$OPENCODE_DATA_ROOT/template" -path '*/.git' -prune -o -type f -name '.env' -print -quit | grep -q .; then
    echo "Refusing to start: workspace template contains a .env file" >&2
    exit 1
  fi

  if [[ ! -f "$OPENCODE_DATA_ROOT/knowledge/README.md" ]]; then
    install -o 10002 -g 10002 -m 0644 "$DEPLOY_DIR/public-knowledge/README.md" "$OPENCODE_DATA_ROOT/knowledge/README.md"
  fi
  chmod 0750 "$OPENCODE_DATA_ROOT"
  chmod 0711 "$OPENCODE_DATA_ROOT/spaces"
  chmod -R a-w "$OPENCODE_DATA_ROOT/template"
  chown -R 10002:10002 "$OPENCODE_DATA_ROOT/knowledge"
  chmod 0755 "$OPENCODE_DATA_ROOT/knowledge"
}

health() {
  load_env
  local response used_mb
  response="$(docker exec insight-opencode node -e 'fetch("http://127.0.0.1:4096/healthz").then(async r=>{if(!r.ok)process.exit(1);process.stdout.write(await r.text())}).catch(()=>process.exit(1))')"
  [[ "$response" == "healthy" ]] && echo "Insight-Agent Runtime Manager is healthy"
  [[ "$(docker inspect insight-opencode --format '{{.State.Health.Status}}')" == "healthy" ]]
  [[ "$(docker inspect insight-opencode-gateway --format '{{.State.Health.Status}}')" == "healthy" ]]
  curl --fail --silent --show-error --max-time 5 "http://127.0.0.1:$OPENCODE_PORT/healthz" >/dev/null
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
    compose restart
    ;;
  upgrade)
    bootstrap
    compose build --pull
    compose up --detach --remove-orphans
    compose up --detach --force-recreate gateway
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
    compose logs --tail 200 --follow
    ;;
  *)
    echo "Usage: $0 {bootstrap|start|stop|restart|upgrade|health|status|logs}" >&2
    exit 2
    ;;
esac
