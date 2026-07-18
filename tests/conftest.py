from __future__ import annotations

import pytest

from vgc_analytics.database import connect, initialize
from vgc_analytics.ingest import ingest_payload


def pokemon(pokemon_id: str, *, item: str | None = None) -> dict:
    return {
        "id": pokemon_id,
        "name": pokemon_id.replace("-", " ").title(),
        "item": item,
        "ability": "Test Ability",
        "nature": "Jolly",
        "tera": "Fire",  # Deliberately present in source; Regulation M-B must ignore it.
        "attacks": ["Protect", "Test Move"],
    }


def standing(player: str, team: list[str] | None, placing: int) -> dict:
    return {
        "player": player,
        "name": player.upper(),
        "country": "ES",
        "placing": placing,
        "record": {"wins": 1, "losses": 1, "ties": 0},
        "drop": None,
        "decklist": [pokemon(value, item="Basculegionite" if value == "basculegion" else None) for value in team] if team else None,
    }


TEAM_A = ["basculegion", "sneasler", "kingambit", "froslass", "incineroar", "garchomp"]
TEAM_B = ["tyranitar", "excadrill", "pelipper", "archaludon", "sinistcha", "garchomp"]
TEAM_C = ["basculegion", "charizard", "whimsicott", "farigiraf", "sylveon", "garchomp"]
TEAM_D = ["charizard", "excadrill", "pelipper", "archaludon", "sinistcha", "garchomp"]


def payload(tournament_id: str, players: int, standings: list[dict], pairings: list[dict]) -> dict:
    return {
        "tournament": {
            "id": tournament_id,
            "name": tournament_id,
            "date": "2026-07-01T10:00:00.000Z",
            "game": "VGC",
            "format": "M-B",
            "players": players,
            "organizerId": 1,
        },
        "standings": standings,
        "pairings": [
            {"phase": 1, "round": index, "table": index, "match": None, **pairing}
            for index, pairing in enumerate(pairings, 1)
        ],
    }


@pytest.fixture
def database(tmp_path):
    path = tmp_path / "test.duckdb"
    initialize(path)
    large = payload(
        "large",
        24,
        [
            standing("a", TEAM_A, 1),
            standing("b", TEAM_B, 2),
            standing("c", TEAM_C, 3),
            standing("unknown", None, 4),
        ],
        [
            {"player1": "a", "player2": "b", "winner": "a"},
            {"player1": "a", "player2": "c", "winner": "c"},
            {"player1": "c", "player2": "b", "winner": 0},
            {"player1": "a", "player2": "", "winner": "a"},
            {"player1": "b", "player2": "unknown", "winner": "b"},
            {"player1": "a", "player2": "b", "winner": -1},
        ],
    )
    small = payload(
        "small",
        10,
        [standing("a2", TEAM_C, 2), standing("b2", TEAM_D, 1)],
        [{"player1": "a2", "player2": "b2", "winner": "b2"}],
    )
    with connect(path) as connection:
        assert ingest_payload(connection, large)
        assert ingest_payload(connection, small)
    return path
