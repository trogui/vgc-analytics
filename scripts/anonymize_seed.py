from __future__ import annotations

import gzip
import json
import sys
from pathlib import Path


def anonymize_tournament(payload: dict) -> int:
    standings = payload.get("standings") or []
    pairings = payload.get("pairings") or []
    player_ids: dict[str, str] = {}

    def alias(value: object) -> str:
        player_id = str(value)
        if player_id not in player_ids:
            player_ids[player_id] = f"player-{len(player_ids) + 1:04d}"
        return player_ids[player_id]

    for standing in standings:
        standing["player"] = alias(standing["player"])
        standing.pop("name", None)
        standing.pop("country", None)

    for pairing in pairings:
        for field in ("player1", "player2"):
            if pairing.get(field) not in (None, ""):
                pairing[field] = alias(pairing[field])
        if str(pairing.get("winner")) not in ("None", "0", "-1"):
            pairing["winner"] = alias(pairing["winner"])

    return len(player_ids)


def main() -> None:
    path = Path(sys.argv[1] if len(sys.argv) > 1 else "data/seed.json.gz")
    with gzip.open(path, "rt", encoding="utf-8") as source:
        snapshot = json.load(source)

    players = sum(anonymize_tournament(payload) for payload in snapshot["tournaments"])
    encoded = json.dumps(snapshot, ensure_ascii=False, separators=(",", ":")).encode()
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_bytes(gzip.compress(encoded, mtime=0))
    temporary.replace(path)
    print(f"Anonymized {players} tournament-local player identifiers in {path}")


if __name__ == "__main__":
    main()
