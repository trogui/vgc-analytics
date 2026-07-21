from __future__ import annotations

import asyncio
import os
import subprocess
import sys

import httpx

from vgc_analytics.app import create_app
from vgc_analytics.ingest import build_from_snapshot


def test_read_only_mode_does_not_register_refresh(database, monkeypatch):
    monkeypatch.setenv("VGC_READ_ONLY", "1")

    async def scenario():
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=create_app(database)), base_url="http://test"
        ) as client:
            assert (await client.post("/api/refresh")).status_code == 404
            assert (await client.get("/api/health")).status_code == 200

    asyncio.run(scenario())


def test_preview_fixture_is_fictional_and_buildable(tmp_path):
    fixture = tmp_path / "preview.json.gz"
    subprocess.run(
        [sys.executable, "scripts/generate_preview_fixture.py", str(fixture)], check=True
    )
    database = tmp_path / "preview.duckdb"
    counts = build_from_snapshot(database, fixture)
    assert counts["inserted_tournaments"] == 4
    assert counts["entries"] == 16


def test_normal_mode_keeps_refresh_route(database, monkeypatch):
    monkeypatch.delenv("VGC_READ_ONLY", raising=False)
    app = create_app(database)
    assert any(route.path == "/api/refresh" for route in app.routes)
