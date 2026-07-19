# Data privacy model

VGC Analytics uses publicly available Play Limitless tournament data for team,
usage, and matchup analysis. Source data remain subject to the Play Limitless
terms and privacy policy.

The public dataset and incremental pipeline are pseudonymized, not anonymous:

- player names and countries are discarded;
- source player/account identifiers are replaced with tournament-local aliases;
- no alias lookup table is retained;
- API and UI responses omit player identity fields;
- event metadata, team lists, placements, and results remain traceable to their
  public source events.

The sanitizer uses explicit source-field allowlists and fails closed when an
unexpected field appears. It runs before a payload is written to `data/raw/` or
normalized into DuckDB.

Generated databases and raw payloads are excluded from Git. Legacy local
artifacts created before this policy may contain identity fields and must be
removed before rebuilding. Backups, exports, request logs, error telemetry, and
screenshots must follow the same no-name/no-account-ID rule.

Corrections or removal requests should be handled through the repository's
owner contact until a dedicated hosted-product process and retention period are
published.
