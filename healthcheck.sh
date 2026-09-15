#!/usr/bin/env bash
set -u

PORT="${UVICORN_PORT:-8000}"
CERTFILE="${UVICORN_SSL_CERTFILE:-}"
KEYFILE="${UVICORN_SSL_KEYFILE:-}"
UDS="${UVICORN_UDS:-}"
HEALTH_PATH="/healthz"

check_http_health() {
    local protocol="$1"
    local host="$2"
    local port="$3"
    local curl_args=(--fail --silent --show-error --max-time 3)

    if [ "$protocol" = "https" ]; then
        curl_args+=(--insecure)
    fi

    curl "${curl_args[@]}" "${protocol}://${host}:${port}${HEALTH_PATH}" >/dev/null
}

check_uds_health() {
    local socket_path="$1"
    [ -S "$socket_path" ] || return 1
    curl --fail --silent --show-error --max-time 3 \
        --unix-socket "$socket_path" "http://localhost${HEALTH_PATH}" >/dev/null
}

if [ -n "$UDS" ]; then
    check_uds_health "$UDS"
    exit $?
fi

if [ -n "$CERTFILE" ] && [ -n "$KEYFILE" ] && [ -f "$CERTFILE" ] && [ -f "$KEYFILE" ]; then
    check_http_health "https" "127.0.0.1" "$PORT"
else
    check_http_health "http" "127.0.0.1" "$PORT"
fi
