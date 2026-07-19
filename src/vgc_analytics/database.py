from __future__ import annotations

from importlib.resources import files
from pathlib import Path

import duckdb


def connect(path: str | Path, *, read_only: bool = False) -> duckdb.DuckDBPyConnection:
    return duckdb.connect(str(path), read_only=read_only)


def initialize(path: str | Path) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    schema = files("vgc_analytics").joinpath("schema.sql").read_text()
    with connect(path) as connection:
        connection.execute(schema)
        columns = {
            row[1]
            for row in connection.execute("PRAGMA table_info('entries')").fetchall()
        }
        for identity_column in ("player_name", "country"):
            if identity_column in columns:
                connection.execute(f"ALTER TABLE entries DROP COLUMN {identity_column}")
        source_ids = connection.execute("""
            SELECT COUNT(*) FROM entries
            WHERE NOT regexp_full_match(player_id, 'player-[0-9]{4,}')
        """).fetchone()[0]
        if source_ids:
            raise RuntimeError(
                "Legacy database contains source player identifiers; rebuild it from the "
                "pseudonymized seed before use"
            )
