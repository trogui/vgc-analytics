#!/bin/zsh
set -e
cd "${0:A:h}"

uv sync
[[ -d frontend/node_modules ]] || npm --prefix frontend install
[[ -f data/vgc_mb.duckdb ]] || uv run vgc-analytics build \
  --snapshot data/seed.json.gz \
  --database data/vgc_mb.duckdb

uv run vgc-analytics serve --database data/vgc_mb.duckdb &
api_pid=$!
trap 'kill "$api_pid" 2>/dev/null || true' EXIT INT TERM

npm --prefix frontend run dev -- --open
