#!/usr/bin/env bash
set -Eeuo pipefail

DEPLOY_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$DEPLOY_DIR/../.." && pwd)"
ENV_FILE="/etc/insight-hermes/hermes.env"

migrate_legacy_config() {
  if [[ ! -f "$ENV_FILE" && -f /etc/insight-opencode/opencode.env ]]; then
    install -D -m 0600 /etc/insight-opencode/opencode.env "$ENV_FILE"
  fi
}

load_env() {
  migrate_legacy_config
  [[ -f "$ENV_FILE" ]] || { echo "Missing $ENV_FILE" >&2; exit 1; }
  set -a
  # shellcheck disable=SC1090
  source "$ENV_FILE"
  set +a
  HERMES_DATA_ROOT="${HERMES_DATA_ROOT:-/var/lib/insight-hermes}"
  HERMES_PORT="${HERMES_PORT:-4096}"
  HERMES_DISK_BUDGET_MB="${HERMES_DISK_BUDGET_MB:-20480}"
  HERMES_MAX_ACTIVE="${HERMES_MAX_ACTIVE:-6}"
  HERMES_IDLE_SECONDS="${HERMES_IDLE_SECONDS:-1800}"
  HERMES_PROVIDER_BASE_URL="${HERMES_PROVIDER_BASE_URL:-${OPENCODE_PROVIDER_BASE_URL:-}}"
  HERMES_PROVIDER_API_KEY="${HERMES_PROVIDER_API_KEY:-${OPENCODE_PROVIDER_API_KEY:-}}"
  : "${HERMES_PROVIDER_BASE_URL:?missing HERMES_PROVIDER_BASE_URL}"
  : "${HERMES_PROVIDER_API_KEY:?missing HERMES_PROVIDER_API_KEY}"
  if [[ -f /etc/insight-hermes/gateway.secret ]]; then
    OPENCODE_GATEWAY_SECRET="$(</etc/insight-hermes/gateway.secret)"
    export OPENCODE_GATEWAY_SECRET
  fi
  export HERMES_DATA_ROOT HERMES_PORT HERMES_DISK_BUDGET_MB HERMES_MAX_ACTIVE HERMES_IDLE_SECONDS HERMES_PROVIDER_BASE_URL HERMES_PROVIDER_API_KEY
}

compose() {
  docker-compose --project-name insight-hermes --file "$DEPLOY_DIR/compose.yaml" "$@"
}

bootstrap() {
  load_env
  install -d -m 0750 /etc/insight-hermes
  if [[ ! -f /etc/insight-hermes/gateway.secret ]]; then
    local gateway_secret="$(openssl rand -hex 32)"
    printf '%s' "$gateway_secret" | install -m 0600 /dev/stdin /etc/insight-hermes/gateway.secret
  fi
  install -o 10001 -g 10001 -m 0400 /etc/insight-hermes/gateway.secret /etc/insight-hermes/backend-gateway.secret
  load_env
  install -d -m 0750 \
    "$HERMES_DATA_ROOT/spaces" \
    "$HERMES_DATA_ROOT/knowledge"

  if [[ ! -d "$HERMES_DATA_ROOT/template/.git" ]]; then
    git clone --no-hardlinks "$PROJECT_ROOT" "$HERMES_DATA_ROOT/template"
    git -C "$HERMES_DATA_ROOT/template" remote set-url origin "$(git -C "$PROJECT_ROOT" remote get-url origin)"
  fi

  if find "$HERMES_DATA_ROOT/template" -path '*/.git' -prune -o -type f -name '.env' -print -quit | grep -q .; then
    echo "Refusing to start: workspace template contains a .env file" >&2
    exit 1
  fi

  if [[ ! -f "$HERMES_DATA_ROOT/knowledge/README.md" ]]; then
    install -o 10002 -g 10002 -m 0644 "$DEPLOY_DIR/public-knowledge/README.md" "$HERMES_DATA_ROOT/knowledge/README.md"
  fi
  chmod 0711 "$HERMES_DATA_ROOT"
  chmod 0711 "$HERMES_DATA_ROOT/spaces"
  chmod -R a-w "$HERMES_DATA_ROOT/template"
  chown -R 10002:10002 "$HERMES_DATA_ROOT/knowledge"
  chmod 0755 "$HERMES_DATA_ROOT/knowledge"
}

health() {
  load_env
  local response used_mb
  response="$(docker exec insight-hermes node -e 'fetch("http://127.0.0.1:4096/healthz").then(async r=>{if(!r.ok)process.exit(1);process.stdout.write(await r.text())}).catch(()=>process.exit(1))')"
  [[ "$response" == "healthy" ]] && echo "Insight-Agent Runtime Manager is healthy"
  [[ "$(docker inspect insight-hermes --format '{{.State.Health.Status}}')" == "healthy" ]]
  [[ "$(docker inspect insight-hermes-gateway --format '{{.State.Health.Status}}')" == "healthy" ]]
  curl --fail --silent --show-error --max-time 5 "http://127.0.0.1:$HERMES_PORT/healthz" >/dev/null
  used_mb="$(du -sm "$HERMES_DATA_ROOT" | awk '{print $1}')"
  if (( used_mb > HERMES_DISK_BUDGET_MB )); then
    echo "Hermes Agent persistent data exceeds budget: ${used_mb} MiB > ${HERMES_DISK_BUDGET_MB} MiB" >&2
    exit 1
  fi
  echo "Persistent data: ${used_mb} MiB / ${HERMES_DISK_BUDGET_MB} MiB budget"
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
