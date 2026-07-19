# VGC Regulation M-B Analytics

A deterministic analytics engine for public Pokémon VGC Regulation M-B
tournaments hosted on Play Limitless. Regulation M-B uses Mega Evolution:
**Terastallization is not part of the model**. Mega Stones remain in each
Pokémon's `item` field.

The application analyzes win rates between team cores and searches for specific
compositions or teamlists. When six Pokémon are selected, set variants can be
compared against a reference by moves, item, ability, and nature.

## Requirements

- Python 3.12 or later.
- [`uv`](https://docs.astral.sh/uv/).
- Node.js 22 or later and npm, only when modifying the frontend.

## Run the application

Start the complete application with one command:

```bash
./run.command
```

On macOS, you can also open `run.command` by double-clicking it.

The application opens at `http://127.0.0.1:8765`.

The server is designed to run locally and does not implement authentication. Do
not expose it directly to the internet.

## Commands

```bash
# Rebuild the database from the bundled snapshot
uv run vgc-analytics build \
  --snapshot data/seed.json.gz \
  --database data/vgc_mb.duckdb

# Verify structural and statistical invariants
uv run vgc-analytics verify --database data/vgc_mb.duckdb

# Run deterministic tests
uv run pytest
```

## Frontend development

The interface uses React, TypeScript, and Vite. FastAPI serves both the API and
the production frontend as a single application.

```bash
./dev.command
```

The script installs dependencies, starts FastAPI, and opens Vite with hot
reload. Press `Ctrl+C` to stop both processes.

Before publishing frontend changes, generate the versioned assets served by the
Python package:

```bash
cd frontend
npm test
npm run build
```

## Calculation semantics

Each valid match produces two rows in `match_sides`, one from each player's
perspective. A win by A over B is represented as `A: W/1.0` and `B: L/0.0`; a
draw produces two `T/0.5` rows.

The displayed win rate is `wins / (wins + losses)`. Draws remain in the record
but do not affect that percentage.

Byes, double losses, invalid results, and matches where either player lacks a
valid public teamlist are excluded by default. Source data problems are retained
in `data_quality_issues`.

## Core queries

Cores are queried directly from the six normalized Pokémon on each team. For
example:

```text
Basculegion + Sneasler + Kingambit
vs Tyranitar + Excadrill
only tournaments with at least 21 players
```

is resolved by filtering each side's Pokémon and aggregating `match_sides`. No
derived combinations are stored, and Pokémon order does not affect the result.

## Data and external services

`data/seed.json.gz` is a reproducible snapshot collected on **July 18, 2026**
through the documented [Play Limitless tournament
endpoints](https://docs.limitlesstcg.com/developer/tournaments). It contains 192
public VGC Regulation M-B tournaments held between June 20 and July 18, 2026.
The snapshot retains standings, pairings, and teamlists, but removes player
names, countries, and source account identifiers. Player references are
replaced with tournament-local aliases using the fail-closed allowlist in
`vgc_analytics.privacy` and `scripts/pseudonymize_seed.py`.

This dataset is deliberately **pseudonymized/de-identified, not anonymous**.
Tournament, team-list, and match-result records remain traceable to their
public source events. Incremental synchronization applies the same sanitizer
before writing a raw response or DuckDB row, and the API/UI never returns a
player name, country, or source account identifier.

Local databases, raw downloads, backups, or exports created before this privacy
change may still contain direct identity fields. Remove those legacy artifacts
and rebuild from the pseudonymized seed before using the updated application.

The data comes from Play Limitless and remains subject to its [Terms of
Service](https://play.limitlesstcg.com/tos) and [Privacy
Policy](https://play.limitlesstcg.com/privacy). Any license applied to this
repository's code grants no additional rights over third-party data. Generated
DuckDB databases and downloaded API responses are excluded from Git.

Pokémon images are loaded in the browser from a pinned version of the [PokéAPI
sprites repository](https://github.com/PokeAPI/sprites) through jsDelivr.

This is an unofficial community project and is not affiliated with Nintendo,
Game Freak, The Pokémon Company, Play Limitless, or PokéAPI.
