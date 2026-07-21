from __future__ import annotations

from importlib.resources import files
from pathlib import Path

import duckdb


PRIVACY_SCHEMA_VERSION = "1"


def connect(path: str | Path, *, read_only: bool = False) -> duckdb.DuckDBPyConnection:
    return duckdb.connect(str(path), read_only=read_only)


def _has_table(connection: duckdb.DuckDBPyConnection, table: str) -> bool:
    return bool(connection.execute("""
        SELECT COUNT(*) FROM information_schema.tables
        WHERE table_schema = 'main' AND table_name = ?
    """, [table]).fetchone()[0])


def _privacy_schema_version(connection: duckdb.DuckDBPyConnection) -> str | None:
    if not _has_table(connection, "app_metadata"):
        return None
    columns = {
        row[1]
        for row in connection.execute("PRAGMA table_info('app_metadata')").fetchall()
    }
    if not {"key", "value"} <= columns:
        return None
    row = connection.execute("""
        SELECT value FROM app_metadata WHERE key = 'privacy_schema_version'
    """).fetchone()
    return str(row[0]) if row else None


def initialize(path: str | Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        with connect(path, read_only=True) as connection:
            if _has_table(connection, "entries"):
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
                has_rows = connection.execute(
                    "SELECT EXISTS (SELECT 1 FROM entries LIMIT 1)"
                ).fetchone()[0]
                if has_rows and _privacy_schema_version(connection) != PRIVACY_SCHEMA_VERSION:
                    raise RuntimeError(
                        "Legacy database is missing the current privacy schema version; "
                        "rebuild it from the pseudonymized seed before use"
                    )
    schema = files("vgc_analytics").joinpath("schema.sql").read_text()
    with connect(path) as connection:
        connection.execute(schema)
        connection.execute("""
            INSERT INTO app_metadata (key, value)
            VALUES ('privacy_schema_version', ?)
            ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value
        """, [PRIVACY_SCHEMA_VERSION])
