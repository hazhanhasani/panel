#!/usr/bin/env bash
set -Eeuo pipefail

ROLE="${ROLE:-all-in-one}"
DATA_DIR="/var/lib/bluepanel"

log() {
    printf '[%s] [BluePanel] %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*"
}

on_error() {
    local rc=$?
    log "ERROR: startup failed with exit code ${rc}"
    exit "$rc"
}
trap on_error ERR

mkdir -p "${DATA_DIR}" "${DATA_DIR}/templates"

case "$ROLE" in
    node)
        log "Starting node worker..."
        exec python node_worker.py
        ;;
    scheduler)
        log "Starting scheduler worker..."
        exec python scheduler_worker.py
        ;;
    all-in-one|backend)
        log "Applying database migrations..."
        python -m alembic upgrade head
        log "Database migrations completed."
        log "Starting BluePanel role=${ROLE}..."
        exec python main.py
        ;;
    *)
        log "ERROR: unsupported ROLE=${ROLE}"
        exit 64
        ;;
esac
