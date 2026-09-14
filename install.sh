#!/usr/bin/env bash
set -Eeuo pipefail

APP_NAME="bluepanel"
REPO="hazhanhasani/panel"
BRANCH="main"
IMAGE="ghcr.io/hazhanhasani/bluepanel:latest"
INSTALL_DIR="/opt/bluepanel"
DATA_DIR="/var/lib/bluepanel"
ENV_FILE="${INSTALL_DIR}/.env"
COMPOSE_FILE="${INSTALL_DIR}/docker-compose.yml"
SELF_PATH="/usr/local/bin/bluepanel"
RAW_BASE="https://raw.githubusercontent.com/${REPO}/${BRANCH}"

log() { printf '\033[1;34m[BluePanel]\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m[BluePanel]\033[0m %s\n' "$*" >&2; }
die() { printf '\033[1;31m[BluePanel]\033[0m %s\n' "$*" >&2; exit 1; }

require_root() {
  [ "$(id -u)" -eq 0 ] || die "Run this command as root (sudo)."
}

ensure_curl() {
  command -v curl >/dev/null 2>&1 && return
  if command -v apt-get >/dev/null 2>&1; then
    apt-get update && apt-get install -y curl ca-certificates
  elif command -v dnf >/dev/null 2>&1; then
    dnf install -y curl ca-certificates
  elif command -v yum >/dev/null 2>&1; then
    yum install -y curl ca-certificates
  else
    die "curl is required. Install curl and run BluePanel again."
  fi
}

ensure_docker() {
  if ! command -v docker >/dev/null 2>&1; then
    log "Docker not found; installing Docker Engine..."
    curl -fsSL https://get.docker.com | sh
  fi
  docker compose version >/dev/null 2>&1 || die "Docker Compose v2 is required."
  systemctl enable --now docker >/dev/null 2>&1 || true
}

install_cli() {
  local tmp
  tmp="$(mktemp)"
  curl -fsSL "${RAW_BASE}/install.sh" -o "$tmp"
  install -m 0755 "$tmp" "$SELF_PATH"
  rm -f "$tmp"
}

sync_project_files() {
  mkdir -p "$INSTALL_DIR" "$DATA_DIR" "$DATA_DIR/templates"

  curl -fsSL "${RAW_BASE}/docker-compose.bluepanel.yml" -o "$COMPOSE_FILE"

  if [ ! -f "$ENV_FILE" ]; then
    curl -fsSL "${RAW_BASE}/.env.example" -o "$ENV_FILE"
    cat >> "$ENV_FILE" <<'EOF'

# BluePanel local data paths
SQLALCHEMY_DATABASE_URL = "sqlite+aiosqlite:////var/lib/bluepanel/db.sqlite3"
CUSTOM_TEMPLATES_DIRECTORY = "/var/lib/bluepanel/templates/"
EOF
  fi
}

pull_image() {
  log "Pulling BluePanel image from ${IMAGE}..."
  if ! docker pull "$IMAGE"; then
    die "Could not pull ${IMAGE}. Make sure the BluePanel build workflow completed and the GHCR package is public/readable."
  fi
}

start_stack() {
  (cd "$INSTALL_DIR" && docker compose -f "$COMPOSE_FILE" -p "$APP_NAME" up -d --remove-orphans)
}

cmd_install() {
  require_root
  ensure_curl
  ensure_docker
  sync_project_files
  install_cli
  pull_image
  start_stack
  log "BluePanel installed successfully."
  log "Dashboard: http://YOUR_SERVER_IP:8000/dashboard/"
  log "Create the owner setup key with: docker exec -it bluepanel-bluepanel-1 bluepanel-cli generate-temp-key"
}

cmd_update() {
  require_root
  ensure_curl
  ensure_docker
  [ -d "$INSTALL_DIR" ] || die "BluePanel is not installed in ${INSTALL_DIR}."
  sync_project_files
  install_cli
  pull_image
  start_stack
  docker image prune -f >/dev/null 2>&1 || true
  log "BluePanel updated from ${REPO}."
}

cmd_restart() {
  require_root
  [ -f "$COMPOSE_FILE" ] || die "BluePanel is not installed."
  (cd "$INSTALL_DIR" && docker compose -f "$COMPOSE_FILE" -p "$APP_NAME" restart)
}

cmd_status() {
  [ -f "$COMPOSE_FILE" ] || die "BluePanel is not installed."
  (cd "$INSTALL_DIR" && docker compose -f "$COMPOSE_FILE" -p "$APP_NAME" ps)
}

cmd_logs() {
  [ -f "$COMPOSE_FILE" ] || die "BluePanel is not installed."
  (cd "$INSTALL_DIR" && docker compose -f "$COMPOSE_FILE" -p "$APP_NAME" logs -f --tail=200)
}

cmd_uninstall() {
  require_root
  if [ -f "$COMPOSE_FILE" ]; then
    (cd "$INSTALL_DIR" && docker compose -f "$COMPOSE_FILE" -p "$APP_NAME" down --remove-orphans) || true
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
  bluepanel uninstall

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
  uninstall) cmd_uninstall ;;
  -h|--help|help) usage ;;
  *) usage; exit 1 ;;
esac
