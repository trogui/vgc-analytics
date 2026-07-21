# syntax=docker/dockerfile:1

FROM node:22-bookworm-slim AS frontend
WORKDIR /build/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim AS builder
WORKDIR /build
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy
RUN pip install --no-cache-dir "uv==0.11.30"
COPY pyproject.toml uv.lock README.md ./
COPY src/ ./src/
COPY scripts/generate_preview_fixture.py ./scripts/generate_preview_fixture.py
RUN uv sync --frozen --no-dev
COPY --from=frontend /build/src/vgc_analytics/static ./src/vgc_analytics/static
RUN .venv/bin/python scripts/generate_preview_fixture.py /tmp/preview-fixture.json.gz \
    && .venv/bin/vgc-analytics build --snapshot /tmp/preview-fixture.json.gz --database /tmp/preview.duckdb \
    && .venv/bin/vgc-analytics verify --database /tmp/preview.duckdb

FROM python:3.12-slim AS runtime
WORKDIR /app
ENV PATH=/build/.venv/bin:$PATH \
    PYTHONDONTWRITEBYTECODE=1 \
    VGC_DATABASE=/app/data/preview.duckdb \
    VGC_READ_ONLY=1 \
    PORT=10000
RUN groupadd --system vgc && useradd --system --gid vgc --home-dir /app vgc
COPY --from=builder --chown=root:root /build/.venv /build/.venv
COPY --from=builder --chown=root:root /build/src /build/src
COPY --from=builder --chown=root:root /tmp/preview.duckdb /app/data/preview.duckdb
RUN chmod 0444 /app/data/preview.duckdb
USER vgc
EXPOSE 10000
CMD ["sh", "-c", "uvicorn vgc_analytics.app:create_app --factory --host 0.0.0.0 --port ${PORT}"]
