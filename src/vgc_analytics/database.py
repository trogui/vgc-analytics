from __future__ import annotations

from importlib.resources import files
from pathlib import Path

import duckdb


def connect(path: str | Path, *, read_only: bool = False) -> duckdb.DuckDBPyConnection:
    return duckdb.connect(str(path), read_only=read_only)


def initialize(path: str | Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        with connect(path, read_only=True) as connection:
            has_entries = connection.execute("""
                SELECT COUNT(*) FROM information_schema.tables
                WHERE table_name = 'entries'
            """).fetchone()[0]
            if has_entries:
                columns = {
                    row[1]
                    for row in connection.execute("PRAGMA table_info('entries')").fetchall()
                }
                identity_columns = columns & {"player_name", "country"}
                if identity_columns:
                    raise RuntimeError(
                        "Legacy database has identity columns; rebuild it from the "
                        "pseudonymized seed before use"
                    )
    schema = files("vgc_analytics").joinpath("schema.sql").read_text()
    with connect(path) as connection:
        connection.execute(schema)
