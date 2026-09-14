ARG PYTHON_VERSION=3.14

FROM oven/bun:1 AS dashboard-builder
WORKDIR /dashboard
COPY dashboard/package.json dashboard/bun.lock ./
RUN bun install
COPY dashboard/ ./
ENV VITE_BASE_API=/
RUN bun run build && cp ./build/index.html ./build/404.html

FROM ghcr.io/astral-sh/uv:python$PYTHON_VERSION-bookworm-slim AS builder
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    libc6-dev \
    && rm -rf /var/lib/apt/lists/*

ENV UV_PYTHON_DOWNLOADS=0

WORKDIR /build
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --no-install-project --no-dev
ADD . /build
COPY --from=dashboard-builder /dashboard/build /build/dashboard/build
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --no-dev

FROM python:$PYTHON_VERSION-slim-bookworm

COPY --from=builder /build /code
WORKDIR /code

ENV PATH="/code/.venv/bin:$PATH"

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    && update-ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY cli_wrapper.sh /usr/bin/bluepanel-cli
RUN chmod +x /usr/bin/bluepanel-cli

COPY healthcheck.sh /code/healthcheck.sh
RUN chmod +x /code/healthcheck.sh
RUN chmod +x /code/start.sh

ENTRYPOINT ["/code/start.sh"]
