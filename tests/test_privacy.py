from __future__ import annotations

import json

import pytest

from vgc_analytics.database import connect, initialize
from vgc_analytics.privacy import sanitize_snapshot, sanitize_tournament_payload


def source_payload() -> dict:
    return {
        "tournament": {
            "id": "event-1",
            "name": "Public Event",
            "date": "2026-07-01T10:00:00.000Z",
            "game": "VGC",
            "format": "M-B",
            "players": 2,
            "organizerId": 42,
        },
        "details": {"isOnline": True},
        "standings": [{
            "player": "source-account-123",
            "name": "Example Person",
            "country": "ES",
            "placing": 1,
            "record": {"wins": 1, "losses": 0, "ties": 0},
            "decklist": [{
                "id": "pikachu",
                "name": "Pikachu",
                "item": "Light Ball",
                "ability": "Static",
                "attacks": ["Thunderbolt", "Protect"],
                "nature": "Timid",
                "tera": None,
            }],
            "deck": {},
            "drop": None,
        }],
        "pairings": [{
            "phase": 1,
            "round": 1,
            "table": 1,
            "match": None,
            "winner": "source-account-123",
            "player1": "source-account-123",
            "player2": "",
        }],
    }


def test_source_identity_is_removed_before_persistence():
    sanitized = sanitize_tournament_payload(source_payload())
    encoded = json.dumps(sanitized)
    assert "Example Person" not in encoded
    assert "source-account-123" not in encoded
    assert '"country"' not in encoded
    assert '"organizerId"' not in encoded
    assert sanitized["standings"][0]["player"] == "player-0001"
    assert sanitized["pairings"][0]["winner"] == "player-0001"
    assert sanitized["pairings"][0]["player1"] == "player-0001"


def test_sanitizer_fails_closed_on_an_unexpected_identity_field():
    payload = source_payload()
    payload["standings"][0]["email"] = "person@example.test"
    with pytest.raises(ValueError, match="Unexpected standing fields: email"):
        sanitize_tournament_payload(payload)


def test_snapshot_sanitization_is_allowlisted_and_source_traceable():
    sanitized = sanitize_snapshot({
        "game": "VGC",
        "format": "M-B",
        "tournaments": [source_payload()],
    })
    assert set(sanitized) == {"game", "format", "tournaments"}
    assert sanitized["tournaments"][0]["tournament"]["id"] == "event-1"
    assert sanitized["tournaments"][0]["tournament"]["name"] == "Public Event"


def test_legacy_database_with_source_ids_fails_closed(tmp_path):
    database = tmp_path / "legacy.duckdb"
    initialize(database)
    with connect(database) as connection:
        connection.execute("""
            INSERT INTO entries VALUES (
                'event-1:source-account-123', 'event-1', 'source-account-123',
                1, 1, 0, 0, FALSE, FALSE
            )
        """)
    with pytest.raises(RuntimeError, match="Legacy database contains source player identifiers"):
        initialize(database)
