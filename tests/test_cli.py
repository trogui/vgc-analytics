from __future__ import annotations

import sys

from fastapi import FastAPI

from vgc_analytics import cli
from vgc_analytics.database import connect, initialize


def test_serve_with_custom_database_ignores_invalid_default(tmp_path, monkeypatch):
    default_database = tmp_path / "data" / "vgc_mb.duckdb"
    initialize(default_database)
    with connect(default_database) as connection:
        connection.execute("DROP TABLE app_metadata")
        connection.execute("""
            INSERT INTO entries VALUES (
                'entry-1', 'event-1', 'source-account-123', 1, 1, 0, 0,
                false, false
            )
        """)

    custom_database = tmp_path / "custom.duckdb"
    initialize(custom_database)
    launched: dict = {}

    def capture_run(app, **options):
        launched["app"] = app
        launched["options"] = options

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(cli.uvicorn, "run", capture_run)
    monkeypatch.setattr(sys, "argv", [
        "vgc-analytics", "serve", "--database", str(custom_database),
    ])

    cli.main()

    assert isinstance(launched["app"], FastAPI)
    assert launched["options"]["host"] == "127.0.0.1"
    with connect(default_database, read_only=True) as connection:
        metadata_tables = connection.execute("""
            SELECT COUNT(*) FROM information_schema.tables
            WHERE table_schema = 'main' AND table_name = 'app_metadata'
        """).fetchone()[0]
    assert metadata_tables == 0
