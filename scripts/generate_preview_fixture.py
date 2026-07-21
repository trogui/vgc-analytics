"""Create the intentionally tiny, fictional dataset used by hosted previews."""

from __future__ import annotations

import gzip
import json
from pathlib import Path


TEAM_A = ("basculegion", "sneasler", "kingambit", "froslass", "incineroar", "garchomp")
TEAM_B = ("tyranitar", "excadrill", "pelipper", "archaludon", "sinistcha", "garchomp")
TEAM_C = ("charizard", "whimsicott", "farigiraf", "sylveon", "incineroar", "rillaboom")
TEAM_D = ("dragonite", "gholdengo", "amoonguss", "arcanine", "rillaboom", "farigiraf")
TEAMS = (TEAM_A, TEAM_B, TEAM_C, TEAM_D)


def pokemon(identifier: str) -> dict[str, object]:
    return {
        "id": identifier,
        "name": identifier.replace("-", " ").title(),
        "item": "Demo Item",
        "ability": "Demo Ability",
        "nature": "Jolly",
        "attacks": ["Protect", "Demo Move"],
    }


def tournament(event: int) -> dict[str, object]:
    players = [f"demo-player-{event}-{seat}" for seat in range(1, 5)]
    standings = [
        {
            "player": player,
            "placing": seat,
            "record": {"wins": 3 - seat // 2, "losses": seat // 2, "ties": 0},
            "decklist": [pokemon(identifier) for identifier in TEAMS[(event + seat - 1) % len(TEAMS)]],
        }
        for seat, player in enumerate(players, 1)
    ]
    pairings = [
        {
            "phase": 1,
            "round": round_number,
            "table": table,
            "match": None,
            "player1": players[first],
            "player2": players[second],
            "winner": players[first if (event + round_number + table) % 2 else second],
        }
        for round_number, first, second, table in ((1, 0, 1, 1), (1, 2, 3, 2), (2, 0, 2, 1), (2, 1, 3, 2))
    ]
    return {
        "tournament": {
            "id": f"preview-fixture-{event:02d}",
            "name": f"Preview Fixture {event:02d}",
            "date": f"2000-01-{event:02d}T12:00:00.000Z",
            "game": "VGC",
            "format": "M-B",
            "players": 4,
        },
        "standings": standings,
        "pairings": pairings,
    }


def snapshot() -> dict[str, object]:
    return {
        "dataset_kind": "synthetic-preview",
        "schema_version": 1,
        "tournaments": [tournament(event) for event in range(1, 5)],
    }


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path)
    arguments = parser.parse_args()
    encoded = json.dumps(snapshot(), sort_keys=True, separators=(",", ":")).encode()
    arguments.path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.GzipFile(arguments.path, "wb", mtime=0) as output:
        output.write(encoded)


if __name__ == "__main__":
    main()
