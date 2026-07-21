from __future__ import annotations

import gzip
import json

import httpx

from vgc_analytics.database import connect
from vgc_analytics.sync import LimitlessClient, sync_database

from conftest import TEAM_A, TEAM_B, payload, standing


def test_sync_discovers_appends_and_then_becomes_a_noop(database, tmp_path):
    new_payload = payload(
        "new",
        32,
        [standing("new-a", TEAM_A, 1), standing("new-b", TEAM_B, 2)],
        [{"player1": "new-a", "player2": "new-b", "winner": "new-a"}],
    )
    for row in new_payload["standings"]:
        row["name"] = f"Source name {row['player']}"
        row["country"] = "ES"
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request.url.path)
        if request.url.path == "/api/tournaments":
            return httpx.Response(200, json=[new_payload["tournament"], {
                "id": "large", "name": "large", "date": "2026-07-01T10:00:00.000Z",
                "game": "VGC", "format": "M-B", "players": 24, "organizerId": 1,
            }])
        endpoint = request.url.path.rsplit("/", 1)[-1]
        if endpoint == "standings":
            return httpx.Response(200, json=new_payload["standings"])
        if endpoint == "pairings":
            return httpx.Response(200, json=new_payload["pairings"])
        raise AssertionError(request.url)

    http = httpx.Client(
        transport=httpx.MockTransport(handler),
        base_url="https://play.limitlesstcg.com/api",
    )
    limitless = LimitlessClient(http, sleep=lambda _: None)
    raw = tmp_path / "raw"
    first = sync_database(database, raw, limitless=limitless)
    assert first["discovered"] == 1
    assert first["inserted"] == 1
    assert first["pending"] == 0
    assert not any(path.endswith("/details") for path in calls)
    assert len(list(raw.glob("*.json.gz"))) == 1
    with gzip.open(next(raw.glob("*.json.gz")), "rt", encoding="utf-8") as handle:
        stored = json.load(handle)
    assert all(set(row).isdisjoint({"name", "country"}) for row in stored["standings"])
    assert {row["player"] for row in stored["standings"]} == {
        "player-0001", "player-0002",
    }
    assert "new-a" not in json.dumps(stored)
    assert "new-b" not in json.dumps(stored)

    calls.clear()
    second = sync_database(database, raw, limitless=limitless)
    assert second == {
        "discovered": 0,
        "inserted": 0,
        "pending": 0,
        "inserted_ids": [],
        "pending_ids": [],
    }
    assert calls == ["/api/tournaments"]
    with connect(database, read_only=True) as connection:
        columns = {row[1] for row in connection.execute("PRAGMA table_info('entries')").fetchall()}
        assert columns.isdisjoint({"player_name", "country"})
        assert connection.execute("SELECT COUNT(*) FROM tournaments").fetchone()[0] == 3
        assert connection.execute("SELECT COUNT(*) FROM ingestion_log WHERE tournament_id='new'").fetchone()[0] == 1
        assert connection.execute(
            "SELECT list(player_id ORDER BY player_id) FROM entries WHERE tournament_id='new'"
        ).fetchone()[0] == ["player-0001", "player-0002"]


def test_unfinished_tournament_is_pending_not_ingested(database, tmp_path):
    tournament = {
        "id": "active", "name": "active", "date": "2026-07-18T10:00:00.000Z",
        "game": "VGC", "format": "M-B", "players": 8, "organizerId": 1,
    }

    def handler(request: httpx.Request) -> httpx.Response:
        endpoint = request.url.path.rsplit("/", 1)[-1]
        if request.url.path == "/api/tournaments":
            return httpx.Response(200, json=[tournament, {
                "id": "large", "name": "large", "date": "2026-07-01T10:00:00.000Z",
                "game": "VGC", "format": "M-B", "players": 24,
            }])
        if endpoint == "standings":
            return httpx.Response(200, json=[{
                "player": "active-a", "name": "A", "placing": None,
                "country": "ES",
                "record": {"wins": 0, "losses": 0, "ties": 0}, "decklist": None,
            }])
        if endpoint == "pairings":
            return httpx.Response(200, json=[])
        raise AssertionError(request.url)

    limitless = LimitlessClient(httpx.Client(
        transport=httpx.MockTransport(handler), base_url="https://play.limitlesstcg.com/api"
    ), sleep=lambda _: None)
    result = sync_database(database, tmp_path / "raw", limitless=limitless)
    assert result["pending_ids"] == ["active"]
    with connect(database, read_only=True) as connection:
        assert connection.execute("SELECT COUNT(*) FROM tournaments WHERE tournament_id='active'").fetchone()[0] == 0
