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
