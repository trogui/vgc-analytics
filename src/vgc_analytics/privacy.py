from __future__ import annotations

from typing import Any, Mapping


PAYLOAD_FIELDS = {"tournament", "details", "standings", "pairings"}
TOURNAMENT_FIELDS = {"id", "name", "date", "game", "format", "players", "organizerId"}
STANDING_FIELDS = {"player", "name", "country", "placing", "record", "decklist", "deck", "drop"}
RECORD_FIELDS = {"wins", "losses", "ties"}
POKEMON_FIELDS = {"id", "name", "item", "ability", "attacks", "nature", "tera"}
PAIRING_FIELDS = {"phase", "round", "table", "match", "winner", "player1", "player2"}
SNAPSHOT_FIELDS = {"game", "format", "tournaments"}


def _reject_unknown(value: Mapping[str, Any], expected: set[str], context: str) -> None:
    unknown = set(value) - expected
    if unknown:
        raise ValueError(f"Unexpected {context} fields: {', '.join(sorted(unknown))}")


def sanitize_tournament_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Return the allowlisted, tournament-locally pseudonymized source payload."""
    _reject_unknown(payload, PAYLOAD_FIELDS, "payload")
    tournament = payload["tournament"]
    _reject_unknown(tournament, TOURNAMENT_FIELDS, "tournament")

    player_aliases: dict[str, str] = {}

    def alias(value: object) -> str:
        source_id = str(value)
        if source_id not in player_aliases:
            player_aliases[source_id] = f"player-{len(player_aliases) + 1:04d}"
        return player_aliases[source_id]

    sanitized_standings = []
    for standing in payload.get("standings") or []:
        _reject_unknown(standing, STANDING_FIELDS, "standing")
        record = standing.get("record") or {}
        _reject_unknown(record, RECORD_FIELDS, "record")
        decklist = []
        for pokemon in standing.get("decklist") or []:
            _reject_unknown(pokemon, POKEMON_FIELDS, "team-list Pokémon")
            decklist.append({
                "id": pokemon["id"],
                "name": pokemon.get("name"),
                "item": pokemon.get("item"),
                "ability": pokemon.get("ability"),
                "attacks": list(pokemon.get("attacks") or []),
                "nature": pokemon.get("nature"),
                "tera": pokemon.get("tera"),
            })
        sanitized_standings.append({
            "player": alias(standing["player"]),
            "placing": standing.get("placing"),
            "record": {
                "wins": record.get("wins"),
                "losses": record.get("losses"),
                "ties": record.get("ties"),
            },
            "decklist": decklist or None,
        })

    sanitized_pairings = []
    for pairing in payload.get("pairings") or []:
        _reject_unknown(pairing, PAIRING_FIELDS, "pairing")

        def pairing_player(field: str) -> str:
            value = pairing.get(field)
            return alias(value) if value not in (None, "") else ""

        winner = pairing.get("winner")
        if str(winner) not in {"None", "0", "-1"}:
            winner = alias(winner)
        sanitized_pairings.append({
            "phase": pairing.get("phase"),
            "round": pairing.get("round"),
            "table": pairing.get("table"),
            "match": pairing.get("match"),
            "winner": winner,
            "player1": pairing_player("player1"),
            "player2": pairing_player("player2"),
        })

    return {
        "tournament": {
            "id": tournament["id"],
            "name": tournament["name"],
            "date": tournament["date"],
            "game": tournament["game"],
            "format": tournament["format"],
            "players": tournament["players"],
        },
        "standings": sanitized_standings,
        "pairings": sanitized_pairings,
    }


def sanitize_snapshot(snapshot: Mapping[str, Any]) -> dict[str, Any]:
    _reject_unknown(snapshot, SNAPSHOT_FIELDS, "snapshot")
    return {
        "game": snapshot["game"],
        "format": snapshot["format"],
        "tournaments": [
            sanitize_tournament_payload(payload)
            for payload in snapshot["tournaments"]
        ],
    }
