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
RAW_BASE="https://raw.githubusercontent.com/${REPO}/${BRANCH}"

log() { printf '\033[1;34m[BluePanel]\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m[BluePanel]\033[0m %s\n' "$*" >&2; }
die() { printf '\033[1;31m[BluePanel]\033[0m %s\n' "$*" >&2; exit 1; }

require_root() {
  [ "$(id -u)" -eq 0 ] || die "Run this command as root (sudo)."
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

sync_source() {
  mkdir -p "$INSTALL_DIR" "$DATA_DIR" "$DATA_DIR/templates"

  if [ -d "${SOURCE_DIR}/.git" ]; then
    log "Updating source from ${REPO}:${BRANCH}..."
    git -C "$SOURCE_DIR" remote set-url origin "$REPO_URL"
    git -C "$SOURCE_DIR" fetch --prune origin "$BRANCH"
    git -C "$SOURCE_DIR" reset --hard "origin/${BRANCH}"
    git -C "$SOURCE_DIR" clean -fd
  else
    rm -rf "$SOURCE_DIR"
    log "Cloning BluePanel from ${REPO}:${BRANCH}..."
    git clone --depth 1 --branch "$BRANCH" "$REPO_URL" "$SOURCE_DIR"
  fi

  cp "${SOURCE_DIR}/docker-compose.bluepanel.yml" "$COMPOSE_FILE"

  if [ ! -f "$ENV_FILE" ]; then
    cp "${SOURCE_DIR}/.env.example" "$ENV_FILE"
    cat >> "$ENV_FILE" <<'EOF'

# BluePanel local data paths
SQLALCHEMY_DATABASE_URL = "sqlite+aiosqlite:////var/lib/bluepanel/db.sqlite3"
CUSTOM_TEMPLATES_DIRECTORY = "/var/lib/bluepanel/templates/"
EOF
  fi
}

build_image() {
  log "Building BluePanel from ${REPO}:${BRANCH}..."
  (cd "$INSTALL_DIR" && docker compose -f "$COMPOSE_FILE" -p "$APP_NAME" build --pull bluepanel)
}

start_stack() {
  (cd "$INSTALL_DIR" && docker compose -f "$COMPOSE_FILE" -p "$APP_NAME" up -d --remove-orphans bluepanel)
}

cmd_install() {
  require_root
  ensure_tools
  ensure_docker
  sync_source
  install_cli
  build_image
  start_stack
  log "BluePanel installed successfully."
  log "Dashboard: http://YOUR_SERVER_IP:8000/dashboard/"
  log "Create the owner setup key with: cd ${INSTALL_DIR} && docker compose -p ${APP_NAME} exec bluepanel bluepanel-cli generate-temp-key"
}

cmd_update() {
  require_root
  ensure_tools
  ensure_docker
  [ -d "$INSTALL_DIR" ] || die "BluePanel is not installed in ${INSTALL_DIR}."
  sync_source
  install_cli
  build_image
  start_stack
  docker image prune -f >/dev/null 2>&1 || true
  log "BluePanel updated only from ${REPO}:${BRANCH}."
}

cmd_restart() {
  require_root
  [ -f "$COMPOSE_FILE" ] || die "BluePanel is not installed."
  (cd "$INSTALL_DIR" && docker compose -f "$COMPOSE_FILE" -p "$APP_NAME" restart bluepanel)
}

cmd_status() {
  [ -f "$COMPOSE_FILE" ] || die "BluePanel is not installed."
  (cd "$INSTALL_DIR" && docker compose -f "$COMPOSE_FILE" -p "$APP_NAME" ps)
}

cmd_logs() {
  [ -f "$COMPOSE_FILE" ] || die "BluePanel is not installed."
  (cd "$INSTALL_DIR" && docker compose -f "$COMPOSE_FILE" -p "$APP_NAME" logs -f --tail=200 bluepanel)
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
