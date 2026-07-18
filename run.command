#!/bin/zsh
set -e
cd "${0:A:h}"
uv sync
if [[ ! -f data/vgc_mb.duckdb ]]; then
  uv run vgc-analytics build \
    --snapshot data/seed.json.gz \
    --database data/vgc_mb.duckdb
fi
uv run vgc-analytics verify --database data/vgc_mb.duckdb
uv run vgc-analytics serve --database data/vgc_mb.duckdb --open
