#!/bin/zsh
set -e
cd "${0:A:h}"

uv sync
[[ -d frontend/node_modules ]] || npm --prefix frontend install
[[ -f data/vgc_mb.duckdb ]] || uv run vgc-analytics build \
  --snapshot data/seed.json.gz \
  --database data/vgc_mb.duckdb

VGC_DATABASE=data/vgc_mb.duckdb uv run uvicorn vgc_analytics.app:create_app --factory --reload --host 127.0.0.1 --port 8765 &
api_pid=$!
trap 'kill "$api_pid" 2>/dev/null || true' EXIT INT TERM

npm --prefix frontend run dev -- --open
