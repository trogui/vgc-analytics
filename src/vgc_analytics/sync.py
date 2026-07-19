from __future__ import annotations

import gzip
import re
import time
from pathlib import Path
from typing import Any

import httpx

from .database import connect, initialize
from .ingest import canonical_json, digest, ingest_payload
from .privacy import sanitize_tournament_payload

BASE_URL = "https://play.limitlesstcg.com/api"
RATE_RE = re.compile(r"r=(\d+);\s*t=(\d+)")


class LimitlessClient:
    def __init__(self, client: httpx.Client | None = None, *, sleep=time.sleep):
        self.client = client or httpx.Client(
            base_url=BASE_URL,
            timeout=60,
            headers={"User-Agent": "vgc-mb-analytics/0.1"},
        )
        self.sleep = sleep

    def get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        for attempt in range(6):
            response = self.client.get(path, params=params)
            if response.status_code == 429 or response.status_code >= 500:
                wait = int(response.headers.get("retry-after", 2 ** attempt)) + 1
                self.sleep(wait)
                continue
            response.raise_for_status()
            rate = RATE_RE.search(response.headers.get("ratelimit", ""))
            if rate and int(rate.group(1)) == 0:
                self.sleep(int(rate.group(2)) + 1)
            return response.json()
        raise RuntimeError(f"Limitless did not return {path} after six attempts")


def discover_new_tournaments(connection, client: LimitlessClient, *, page_size: int = 200) -> list[dict[str, Any]]:
    known = {
        row[0]
        for row in connection.execute("SELECT tournament_id FROM ingestion_log").fetchall()
    }
    discovered: dict[str, dict[str, Any]] = {}
    page = 0
    while True:
        tournaments = client.get("/tournaments", {
            "game": "VGC", "format": "M-B", "limit": page_size, "page": page,
        })
        if not tournaments:
            break
        page_contains_known = False
        for tournament in tournaments:
            if tournament["id"] in known:
                page_contains_known = True
            else:
                discovered[tournament["id"]] = tournament
        if page_contains_known or len(tournaments) < page_size:
            break
        page += 1
    return sorted(discovered.values(), key=lambda value: (value["date"], value["id"]))


def is_finished(payload: dict[str, Any]) -> bool:
    standings = payload.get("standings") or []
    pairings = payload.get("pairings") or []
    return bool(pairings) and any(entry.get("placing") is not None for entry in standings)


def preserve_raw(payload: dict[str, Any], raw_directory: str | Path) -> Path:
    raw_directory = Path(raw_directory)
    raw_directory.mkdir(parents=True, exist_ok=True)
    source_hash = digest(payload)
    destination = raw_directory / f"{source_hash}.json.gz"
    if not destination.exists():
        temporary = destination.with_suffix(".tmp")
        with gzip.open(temporary, "wt", encoding="utf-8") as handle:
            handle.write(canonical_json(payload))
        temporary.replace(destination)
    return destination


def sync_database(
    database_path: str | Path,
    raw_directory: str | Path,
    *,
    limitless: LimitlessClient | None = None,
) -> dict[str, Any]:
    database_path = Path(database_path)
    initialize(database_path)
    client = limitless or LimitlessClient()
    inserted: list[str] = []
    pending: list[str] = []
    with connect(database_path) as connection:
        tournaments = discover_new_tournaments(connection, client)
        for tournament in tournaments:
            tournament_id = tournament["id"]
            payload = {
                "tournament": tournament,
                "details": client.get(f"/tournaments/{tournament_id}/details"),
                "standings": client.get(f"/tournaments/{tournament_id}/standings"),
                "pairings": client.get(f"/tournaments/{tournament_id}/pairings"),
            }
            payload = sanitize_tournament_payload(payload)
            preserve_raw(payload, raw_directory)
            if not is_finished(payload):
                pending.append(tournament_id)
                continue
            if ingest_payload(connection, payload):
                inserted.append(tournament_id)
    return {
        "discovered": len(tournaments),
        "inserted": len(inserted),
        "pending": len(pending),
        "inserted_ids": inserted,
        "pending_ids": pending,
    }
