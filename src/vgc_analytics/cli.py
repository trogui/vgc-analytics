from __future__ import annotations

import argparse
import json
import threading
import webbrowser

import uvicorn

from .ingest import build_from_snapshot
from .sync import sync_database
from .validate import validate_database


def parser() -> argparse.ArgumentParser:
    command = argparse.ArgumentParser(prog="vgc-analytics")
    subcommands = command.add_subparsers(dest="command", required=True)

    build = subcommands.add_parser("build", help="Build DuckDB from the initial raw snapshot")
    build.add_argument("--snapshot", default="../limitless-vgc-reg-mb-dump/raw.json.gz")
    build.add_argument("--database", default="data/vgc_mb.duckdb")

    sync = subcommands.add_parser("sync", help="Append finished tournaments not yet ingested")
    sync.add_argument("--database", default="data/vgc_mb.duckdb")
    sync.add_argument("--raw", default="data/raw")

    serve = subcommands.add_parser("serve", help="Run the local analytics application")
    serve.add_argument("--database", default="data/vgc_mb.duckdb")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", default=8765, type=int)
    serve.add_argument("--open", action="store_true")

    verify = subcommands.add_parser("verify", help="Run structural and statistical invariants")
    verify.add_argument("--database", default="data/vgc_mb.duckdb")
    return command


def main() -> None:
    arguments = parser().parse_args()
    if arguments.command == "build":
        result = build_from_snapshot(arguments.database, arguments.snapshot)
        print(json.dumps(result, indent=2))
    elif arguments.command == "sync":
        result = sync_database(arguments.database, arguments.raw)
        print(json.dumps(result, indent=2))
    elif arguments.command == "serve":
        from .app import create_app

        if arguments.open:
            threading.Timer(0.8, lambda: webbrowser.open(f"http://{arguments.host}:{arguments.port}")).start()
        uvicorn.run(create_app(arguments.database), host=arguments.host, port=arguments.port)
    elif arguments.command == "verify":
        print(json.dumps(validate_database(arguments.database), indent=2))


if __name__ == "__main__":
    main()
