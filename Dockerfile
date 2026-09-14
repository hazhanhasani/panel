ARG PYTHON_VERSION=3.14

# The dashboard is built once by CI (build.yml / build-dev.yml) and downloaded
# into dashboard/build before this image is built. Keep the Docker build focused
# on the Python application so the frontend dependency graph is not rebuilt twice.
FROM ghcr.io/astral-sh/uv:python$PYTHON_VERSION-bookworm-slim AS builder
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    git \
    python3-dev \
    libc6-dev \
    && rm -rf /var/lib/apt/lists/*

ENV UV_PYTHON_DOWNLOADS=0

WORKDIR /build
ADD . /build
RUN test -f /build/dashboard/build/index.html
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

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
