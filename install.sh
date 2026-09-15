#!/usr/bin/env bash
set -Eeuo pipefail

APP_NAME="bluepanel"
REPO="hazhanhasani/panel"
BRANCH="main"
REPO_URL="https://github.com/${REPO}.git"
INSTALL_DIR="/opt/bluepanel"
SOURCE_DIR="${INSTALL_DIR}/source"
DATA_DIR="/var/lib/bluepanel"
ENV_FILE="${INSTALL_DIR}/.env"
COMPOSE_FILE="${INSTALL_DIR}/docker-compose.yml"
SELF_PATH="/usr/local/bin/bluepanel"
DEFAULT_PORT="8000"
HEALTH_TIMEOUT="${BLUEPANEL_HEALTH_TIMEOUT:-180}"
ROLLBACK_IMAGE="bluepanel:rollback"

log() { printf '\033[1;34m[BluePanel]\033[0m %s\n' "$*"; }
ok() { printf '\033[1;32m[BluePanel]\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m[BluePanel]\033[0m %s\n' "$*" >&2; }
die() { printf '\033[1;31m[BluePanel]\033[0m %s\n' "$*" >&2; exit 1; }

require_root() {
  [ "$(id -u)" -eq 0 ] || die "Run this command as root (sudo)."
  [ "$(uname -s)" = "Linux" ] || die "BluePanel Docker installer currently supports Linux only."
}

install_packages() {
  local packages=("$@")
  if command -v apt-get >/dev/null 2>&1; then
    apt-get update
    DEBIAN_FRONTEND=noninteractive apt-get install -y "${packages[@]}"
  elif command -v dnf >/dev/null 2>&1; then
    dnf install -y "${packages[@]}"
  elif command -v yum >/dev/null 2>&1; then
    yum install -y "${packages[@]}"
  else
    die "Unsupported package manager. Install curl, git and Docker manually."
  fi
}

ensure_tools() {
  command -v curl >/dev/null 2>&1 || install_packages curl ca-certificates
  command -v git >/dev/null 2>&1 || install_packages git ca-certificates
}

ensure_docker() {
  if ! command -v docker >/dev/null 2>&1; then
    log "Docker not found; installing Docker Engine..."
    curl -fsSL https://get.docker.com | sh
  fi

  if command -v systemctl >/dev/null 2>&1; then
    systemctl enable --now docker >/dev/null 2>&1 || true
  fi

  docker info >/dev/null 2>&1 || die "Docker daemon is not running or is not accessible."
  docker compose version >/dev/null 2>&1 || die "Docker Compose v2 is required."
}

compose() {
  (cd "$INSTALL_DIR" && docker compose -f "$COMPOSE_FILE" -p "$APP_NAME" "$@")
}

container_id() {
  compose ps -q bluepanel 2>/dev/null | head -n1
}

show_diagnostics() {
  [ -f "$COMPOSE_FILE" ] || return 0
  warn "BluePanel diagnostics:"
  compose ps || true
  compose logs --no-color --tail=200 bluepanel || true
}

sync_source() {
  mkdir -p "$INSTALL_DIR" "$DATA_DIR" "$DATA_DIR/templates"

  if [ -d "${SOURCE_DIR}/.git" ]; then
    log "Updating source from ${REPO}:${BRANCH}..."
    git -C "$SOURCE_DIR" remote set-url origin "$REPO_URL"
    git -C "$SOURCE_DIR" fetch --depth 1 --prune origin "$BRANCH"
    git -C "$SOURCE_DIR" reset --hard "origin/${BRANCH}"
    git -C "$SOURCE_DIR" clean -fd
  else
    rm -rf "$SOURCE_DIR"
    log "Cloning BluePanel from ${REPO}:${BRANCH}..."
    git clone --depth 1 --branch "$BRANCH" "$REPO_URL" "$SOURCE_DIR"
  fi

  [ -f "${SOURCE_DIR}/docker-compose.bluepanel.yml" ] || die "docker-compose.bluepanel.yml is missing from source."
  [ -f "${SOURCE_DIR}/Dockerfile" ] || die "Dockerfile is missing from source."
  cp "${SOURCE_DIR}/docker-compose.bluepanel.yml" "$COMPOSE_FILE"
}

set_env_value() {
  local key="$1"
  local value="$2"
  if grep -Eq "^[[:space:]]*${key}[[:space:]]*=" "$ENV_FILE"; then
    sed -i -E "s|^[[:space:]]*${key}[[:space:]]*=.*$|${key} = ${value}|" "$ENV_FILE"
  else
    printf '%s = %s\n' "$key" "$value" >> "$ENV_FILE"
  fi
}

ensure_env() {
  if [ ! -f "$ENV_FILE" ]; then
    log "Creating ${ENV_FILE}..."
    cp "${SOURCE_DIR}/.env.example" "$ENV_FILE"
    cat >> "$ENV_FILE" <<'EOF'

# BluePanel persistent data
SQLALCHEMY_DATABASE_URL = "sqlite+aiosqlite:////var/lib/bluepanel/db.sqlite3"
CUSTOM_TEMPLATES_DIRECTORY = "/var/lib/bluepanel/templates/"
EOF

    if [ -n "${BLUEPANEL_PORT:-}" ]; then
      [[ "$BLUEPANEL_PORT" =~ ^[0-9]+$ ]] || die "BLUEPANEL_PORT must be numeric."
      (( BLUEPANEL_PORT >= 1 && BLUEPANEL_PORT <= 65535 )) || die "BLUEPANEL_PORT must be between 1 and 65535."
      set_env_value "UVICORN_PORT" "$BLUEPANEL_PORT"
    fi

    if [ -n "${BLUEPANEL_HOST:-}" ]; then
      set_env_value "UVICORN_HOST" "\"${BLUEPANEL_HOST}\""
    fi
  fi
}

service_port() {
  local port
  port="$(sed -nE 's/^[[:space:]]*UVICORN_PORT[[:space:]]*=[[:space:]]*"?([0-9]+)"?.*/\1/p' "$ENV_FILE" | tail -n1)"
  printf '%s\n' "${port:-$DEFAULT_PORT}"
}

validate_port() {
  local port="$1"
  [[ "$port" =~ ^[0-9]+$ ]] || die "Invalid UVICORN_PORT in ${ENV_FILE}: ${port}"
  (( port >= 1 && port <= 65535 )) || die "UVICORN_PORT must be between 1 and 65535."
}

port_in_use() {
  local port="$1"
  command -v ss >/dev/null 2>&1 || return 1
  ss -ltn 2>/dev/null | awk 'NR > 1 {print $4}' | grep -Eq "[:.]${port}$|\]:${port}$"
}

preflight() {
  local port
  port="$(service_port)"
  validate_port "$port"

  log "Validating Docker Compose configuration..."
  compose config -q || die "Docker Compose configuration is invalid."

  if [ -z "$(container_id)" ] && port_in_use "$port"; then
    die "Port ${port} is already in use. Set BLUEPANEL_PORT before the first install or edit ${ENV_FILE}."
  fi
}

install_cli() {
  [ -f "${SOURCE_DIR}/install.sh" ] || die "Installer source is missing."
  install -m 0755 "${SOURCE_DIR}/install.sh" "$SELF_PATH"
}

build_image() {
  log "Building BluePanel image..."
  local build_args=(build bluepanel)
  if [ "${BLUEPANEL_PULL:-0}" = "1" ]; then
    build_args=(build --pull bluepanel)
  fi

  if ! compose "${build_args[@]}"; then
    show_diagnostics
    die "Docker image build failed."
  fi
}

start_stack() {
  log "Starting BluePanel..."
  if ! compose up -d --remove-orphans bluepanel; then
    show_diagnostics
    die "Docker Compose failed to start BluePanel."
  fi
}

wait_for_health() {
  local port id state health elapsed=0
  port="$(service_port)"
  id="$(container_id)"
  [ -n "$id" ] || { show_diagnostics; die "BluePanel container was not created."; }

  log "Waiting for BluePanel health check (timeout ${HEALTH_TIMEOUT}s)..."
  while (( elapsed < HEALTH_TIMEOUT )); do
    state="$(docker inspect -f '{{.State.Status}}' "$id" 2>/dev/null || true)"
    health="$(docker inspect -f '{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' "$id" 2>/dev/null || true)"

    if [ "$state" = "exited" ] || [ "$state" = "dead" ]; then
      show_diagnostics
      die "BluePanel container stopped during startup."
    fi

    if [ "$health" = "healthy" ]; then
      if curl -fsS --max-time 5 "http://127.0.0.1:${port}/healthz" >/dev/null 2>&1; then
        ok "BluePanel is healthy on port ${port}."
        return 0
      fi
    fi

    sleep 2
    elapsed=$((elapsed + 2))
  done

  show_diagnostics
  die "BluePanel did not become healthy within ${HEALTH_TIMEOUT}s."
}

backup_sqlite() {
  local db="${DATA_DIR}/db.sqlite3"
  if [ -f "$db" ]; then
    local backup="${DATA_DIR}/db.sqlite3.backup-$(date +%Y%m%d-%H%M%S)"
    cp -a "$db" "$backup"
    log "Database backup: ${backup}"
  fi
}

save_rollback_image() {
  if docker image inspect bluepanel:local >/dev/null 2>&1; then
    docker tag bluepanel:local "$ROLLBACK_IMAGE"
  fi
}

rollback_image() {
  if ! docker image inspect "$ROLLBACK_IMAGE" >/dev/null 2>&1; then
    return 1
  fi
  warn "Restoring previous BluePanel image..."
  docker tag "$ROLLBACK_IMAGE" bluepanel:local
  compose up -d --no-build --remove-orphans bluepanel || return 1
  return 0
}

print_access_info() {
  local port
  port="$(service_port)"
  ok "BluePanel is installed and healthy."
  log "Dashboard: http://YOUR_SERVER_IP:${port}/dashboard/"
  log "Manager commands: bluepanel status | bluepanel logs | bluepanel doctor | bluepanel update"
}

cmd_install() {
  require_root
  ensure_tools
  ensure_docker
  sync_source
  ensure_env
  install_cli
  preflight
  build_image
  start_stack
  wait_for_health
  print_access_info
  log "Generating one-time owner setup key..."
  if ! compose exec -T bluepanel bluepanel-cli generate-temp-key; then
    warn "Panel is healthy, but the setup key could not be generated automatically."
    warn "Run: cd ${INSTALL_DIR} && docker compose -p ${APP_NAME} exec bluepanel bluepanel-cli generate-temp-key"
  fi
}

cmd_update() {
  require_root
  ensure_tools
  ensure_docker
  [ -d "$INSTALL_DIR" ] || die "BluePanel is not installed in ${INSTALL_DIR}."
  [ -f "$ENV_FILE" ] || die "BluePanel environment file is missing: ${ENV_FILE}"

  backup_sqlite
  save_rollback_image
  sync_source
  install_cli
  preflight

  if ! build_image || ! start_stack || ! wait_for_health; then
    warn "Update failed. Attempting image rollback..."
    if rollback_image; then
      warn "Previous image restored. Check logs with: bluepanel logs"
    fi
    exit 1
  fi

  docker image rm "$ROLLBACK_IMAGE" >/dev/null 2>&1 || true
  docker image prune -f >/dev/null 2>&1 || true
  ok "BluePanel update completed and passed health checks."
}

cmd_restart() {
  require_root
  [ -f "$COMPOSE_FILE" ] || die "BluePanel is not installed."
  compose restart bluepanel
  wait_for_health
}

cmd_status() {
  [ -f "$COMPOSE_FILE" ] || die "BluePanel is not installed."
  compose ps
}

cmd_logs() {
  [ -f "$COMPOSE_FILE" ] || die "BluePanel is not installed."
  compose logs -f --tail=200 bluepanel
}

cmd_doctor() {
  require_root
  [ -f "$COMPOSE_FILE" ] || die "BluePanel is not installed."
  [ -f "$ENV_FILE" ] || die "BluePanel environment file is missing."
  ensure_docker

  local port id state health
  port="$(service_port)"
  validate_port "$port"

  log "Compose config..."
  compose config -q && ok "Compose config: OK" || die "Compose config: FAILED"

  id="$(container_id)"
  if [ -z "$id" ]; then
    show_diagnostics
    die "Container: missing"
  fi

  state="$(docker inspect -f '{{.State.Status}}' "$id")"
  health="$(docker inspect -f '{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' "$id")"
  log "Container state: ${state}; health: ${health}"

  if curl -fsS --max-time 5 "http://127.0.0.1:${port}/healthz" >/dev/null; then
    ok "HTTP health endpoint: OK"
  else
    show_diagnostics
    die "HTTP health endpoint: FAILED"
  fi

  ok "BluePanel doctor found no installation/runtime errors."
}

cmd_uninstall() {
  require_root
  if [ -f "$COMPOSE_FILE" ]; then
    compose down --remove-orphans || true
  fi
  rm -rf "$INSTALL_DIR"
  rm -f "$SELF_PATH"
  warn "BluePanel application files were removed. Data was kept in ${DATA_DIR}."
}

usage() {
  cat <<'EOF'
BluePanel manager

Usage:
  bluepanel install
  bluepanel update
  bluepanel restart
  bluepanel status
  bluepanel logs
  bluepanel doctor
  bluepanel uninstall

Optional first-install variables:
  BLUEPANEL_PORT=8000
  BLUEPANEL_HOST=0.0.0.0
  BLUEPANEL_PULL=1

One-line install:
  sudo bash -c "$(curl -fsSL https://raw.githubusercontent.com/hazhanhasani/panel/main/install.sh)" @ install
EOF
}

if [ "${1:-}" = "@" ]; then shift; fi
case "${1:-install}" in
  install) cmd_install ;;
  update) cmd_update ;;
  restart) cmd_restart ;;
  status) cmd_status ;;
  logs) cmd_logs ;;
  doctor) cmd_doctor ;;
  uninstall) cmd_uninstall ;;
  -h|--help|help) usage ;;
  *) usage; exit 1 ;;
esac
