from __future__ import annotations

import gzip
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

import pyarrow as pa

from .database import connect, initialize
from .privacy import sanitize_tournament_payload


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode()).hexdigest()


def entry_id(tournament_id: str, player_id: str) -> str:
    return f"{tournament_id}:{player_id}"


def core_key(pokemon_ids: Iterable[str]) -> str:
    values = sorted({value.strip().lower() for value in pokemon_ids if value})
    return "|".join(values)


def _insert_rows(connection, table: str, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    batch = pa.Table.from_pylist(rows)
    columns = ", ".join(f'"{column}"' for column in batch.column_names)
    connection.register("_batch", batch)
    try:
        connection.execute(f"INSERT INTO {table} ({columns}) SELECT {columns} FROM _batch")
    finally:
        connection.unregister("_batch")


def normalize_tournament(payload: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    tournament = payload["tournament"]
    standings = payload.get("standings") or []
    pairings = payload.get("pairings") or []
    tournament_id = tournament["id"]
    source_hash = digest(payload)

    rows: dict[str, list[dict[str, Any]]] = {
        name: []
        for name in (
            "tournaments", "entries", "teams", "team_pokemon", "team_moves",
            "matches", "match_sides", "ingestion_log", "data_quality_issues",
        )
    }
    rows["tournaments"].append({
        "tournament_id": tournament_id,
        "name": tournament["name"],
        "tournament_date": tournament["date"],
        "game": tournament["game"],
        "format": tournament["format"],
        "listed_players": tournament["players"],
        "source_hash": source_hash,
    })

    known_entries: set[str] = set()
    valid_team_entries: set[str] = set()
    for standing in standings:
        player_id = str(standing["player"])
        current_entry_id = entry_id(tournament_id, player_id)
        known_entries.add(current_entry_id)
        record = standing.get("record") or {}
        teamlist = standing.get("decklist") or []
        entry_row = {
            "entry_id": current_entry_id,
            "tournament_id": tournament_id,
            "player_id": player_id,
            "final_placing": standing.get("placing"),
            "wins": record.get("wins"),
            "losses": record.get("losses"),
            "ties": record.get("ties"),
            "has_teamlist": bool(teamlist),
            "teamlist_valid": False,
        }
        rows["entries"].append(entry_row)
        if not teamlist:
            continue
        if len(teamlist) != 6:
            rows["data_quality_issues"].append({
                "issue_id": digest([current_entry_id, "team_size"]),
                "tournament_id": tournament_id,
                "entry_id": current_entry_id,
                "code": "invalid_team_size",
                "detail": f"Expected 6 Pokémon, got {len(teamlist)}",
            })
            continue

        pokemon_ids = [str(pokemon["id"]).lower() for pokemon in teamlist]
        if len(set(pokemon_ids)) != 6:
            duplicates = sorted(value for value, count in Counter(pokemon_ids).items() if count > 1)
            rows["data_quality_issues"].append({
                "issue_id": digest([current_entry_id, "duplicate_species"]),
                "tournament_id": tournament_id,
                "entry_id": current_entry_id,
                "code": "duplicate_species",
                "detail": f"Duplicate Pokémon: {', '.join(duplicates)}",
            })
            continue
        oversized_moves = [
            slot for slot, pokemon in enumerate(teamlist, 1)
            if len(pokemon.get("attacks") or []) > 4
        ]
        if oversized_moves:
            rows["data_quality_issues"].append({
                "issue_id": digest([current_entry_id, "too_many_moves"]),
                "tournament_id": tournament_id,
                "entry_id": current_entry_id,
                "code": "too_many_moves",
                "detail": f"More than four moves in slots: {oversized_moves}",
            })
            continue
        entry_row["teamlist_valid"] = True
        composition = core_key(pokemon_ids)
        sheet = []
        for slot, pokemon in enumerate(teamlist, 1):
            moves = list(pokemon.get("attacks") or [])
            rows["team_pokemon"].append({
                "entry_id": current_entry_id,
                "slot": slot,
                "pokemon_id": pokemon_ids[slot - 1],
                "pokemon_name": pokemon.get("name") or pokemon_ids[slot - 1],
                "item": pokemon.get("item"),
                "ability": pokemon.get("ability"),
                "nature": pokemon.get("nature"),
            })
            for move_slot, move in enumerate(moves, 1):
                rows["team_moves"].append({
                    "entry_id": current_entry_id,
                    "pokemon_slot": slot,
                    "move_slot": move_slot,
                    "move": move,
                })
            sheet.append({
                "pokemon_id": pokemon_ids[slot - 1],
                "item": pokemon.get("item"),
                "ability": pokemon.get("ability"),
                "nature": pokemon.get("nature"),
                "moves": sorted(moves),
            })
        rows["teams"].append({
            "entry_id": current_entry_id,
            "composition_key": composition,
            "open_sheet_key": digest(sorted(sheet, key=lambda value: value["pokemon_id"])),
        })
        valid_team_entries.add(current_entry_id)

    occurrences: Counter[str] = Counter()
    for pairing in pairings:
        player1 = str(pairing.get("player1") or "")
        player2 = str(pairing.get("player2") or "")
        base = {
            "tournament_id": tournament_id,
            "phase": pairing.get("phase"),
            "round": pairing.get("round"),
            "table": pairing.get("table"),
            "match": pairing.get("match"),
            "player1": player1,
            "player2": player2,
        }
        base_key = canonical_json(base)
        occurrence = occurrences[base_key]
        occurrences[base_key] += 1
        match_id = digest({"match": base, "occurrence": occurrence})
        p1_entry = entry_id(tournament_id, player1) if player1 else None
        p2_entry = entry_id(tournament_id, player2) if player2 else None
        winner = str(pairing.get("winner"))

        if not player2:
            status, winner_entry = "bye", None
        elif winner == "0":
            status, winner_entry = "tie", None
        elif winner == "-1":
            status, winner_entry = "double_loss", None
        elif winner == player1:
            status, winner_entry = "decided", p1_entry
        elif winner == player2:
            status, winner_entry = "decided", p2_entry
        else:
            status, winner_entry = "invalid", None

        rows["matches"].append({
            "match_id": match_id,
            "tournament_id": tournament_id,
            "phase": pairing.get("phase"),
            "round": pairing.get("round"),
            "table_number": pairing.get("table"),
            "match_label": pairing.get("match"),
            "player1_entry_id": p1_entry,
            "player2_entry_id": p2_entry,
            "winner_entry_id": winner_entry,
            "status": status,
        })
        if not p1_entry or not p2_entry or p1_entry not in known_entries or p2_entry not in known_entries:
            continue
        if status == "decided":
            p1_outcome = "W" if winner_entry == p1_entry else "L"
            p2_outcome = "W" if winner_entry == p2_entry else "L"
            side_values = [(1, p1_entry, p2_entry, p1_outcome), (2, p2_entry, p1_entry, p2_outcome)]
        elif status == "tie":
            side_values = [(1, p1_entry, p2_entry, "T"), (2, p2_entry, p1_entry, "T")]
        elif status == "double_loss":
            side_values = [(1, p1_entry, p2_entry, "L"), (2, p2_entry, p1_entry, "L")]
        else:
            side_values = []
        for side, own, opponent, outcome in side_values:
            rows["match_sides"].append({
                "match_id": match_id,
                "side": side,
                "tournament_id": tournament_id,
                "own_entry_id": own,
                "opponent_entry_id": opponent,
                "outcome": outcome,
                "score": {"W": 1.0, "T": 0.5, "L": 0.0}[outcome],
                "competitive": status in {"decided", "tie"},
                "analyzable": (
                    status in {"decided", "tie"}
                    and own in valid_team_entries
                    and opponent in valid_team_entries
                ),
            })

    rows["ingestion_log"].append({
        "tournament_id": tournament_id,
        "source_hash": source_hash,
    })
    return rows


def ingest_payload(connection, payload: dict[str, Any]) -> bool:
    tournament_id = payload["tournament"]["id"]
    existing = connection.execute(
        "SELECT 1 FROM ingestion_log WHERE tournament_id = ?", [tournament_id]
    ).fetchone()
    if existing:
        return False
    rows = normalize_tournament(payload)
    connection.execute("BEGIN TRANSACTION")
    try:
        for table in (
            "tournaments", "entries", "teams", "team_pokemon", "team_moves",
            "matches", "match_sides", "ingestion_log", "data_quality_issues",
        ):
            _insert_rows(connection, table, rows[table])
        connection.execute("COMMIT")
    except Exception:
        connection.execute("ROLLBACK")
        raise
    return True


def build_from_snapshot(database_path: str | Path, snapshot_path: str | Path) -> dict[str, int]:
    database_path = Path(database_path)
    database_path.unlink(missing_ok=True)
    initialize(database_path)
    with gzip.open(snapshot_path, "rt", encoding="utf-8") as handle:
        snapshot = json.load(handle)
    inserted = 0
    with connect(database_path) as connection:
        for payload in sorted(
            snapshot["tournaments"],
            key=lambda value: (value["tournament"]["date"], value["tournament"]["id"]),
        ):
            inserted += ingest_payload(connection, sanitize_tournament_payload(payload))
    with connect(database_path, read_only=True) as connection:
        counts = {
            table: connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            for table in ("tournaments", "entries", "teams", "team_pokemon", "team_moves", "matches", "match_sides", "data_quality_issues")
        }
    counts["inserted_tournaments"] = inserted
    return counts
