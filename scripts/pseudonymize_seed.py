from __future__ import annotations

import gzip
import json
import sys
from pathlib import Path

from vgc_analytics.privacy import sanitize_snapshot


def main() -> None:
    path = Path(sys.argv[1] if len(sys.argv) > 1 else "data/seed.json.gz")
    with gzip.open(path, "rt", encoding="utf-8") as source:
        source_snapshot = json.load(source)

    snapshot = sanitize_snapshot(source_snapshot)
    encoded = json.dumps(
        snapshot, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode()
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_bytes(gzip.compress(encoded, mtime=0))
    temporary.replace(path)
    print(f"Pseudonymized allowlisted tournament data in {path}")


if __name__ == "__main__":
    main()
