from __future__ import annotations

import os
import threading
from importlib.resources import files
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from .database import connect, initialize
from .engine import AnalysisQuery, AnalyticsEngine, TeamSearchQuery, TournamentFilter
from .sync import sync_database


def create_app(database_path: str | Path | None = None, raw_directory: str | Path | None = None) -> FastAPI:
    path = Path(database_path or os.getenv("VGC_DATABASE", "data/vgc_mb.duckdb"))
    raw_path = Path(raw_directory or os.getenv("VGC_RAW", "data/raw"))
    if path.exists():
        initialize(path)
    app = FastAPI(title="VGC Analytics", version="0.1.0")
    engine = AnalyticsEngine(path)
    refresh_lock = threading.Lock()
    static_path = files("vgc_analytics").joinpath("static")

    @app.get("/", response_class=HTMLResponse, include_in_schema=False)
    @app.get("/teams", response_class=HTMLResponse, include_in_schema=False)
    def index():
        return static_path.joinpath("index.html").read_text()

    @app.get("/api/health")
    def health():
        if not path.exists():
            raise HTTPException(503, f"Database not found: {path}")
        with connect(path, read_only=True) as connection:
            tournaments, matches, teams = connection.execute("""
                SELECT
                    (SELECT COUNT(*) FROM tournaments),
                    (SELECT COUNT(*) FROM matches),
                    (SELECT COUNT(*) FROM teams)
            """).fetchone()
        return {"status": "ok", "tournaments": tournaments, "matches": matches, "teams": teams}

    @app.get("/api/species")
    def species(min_players: int = Query(1, ge=1)):
        return engine.species(TournamentFilter(min_players=min_players))

    @app.get("/api/species/{pokemon_id}/options")
    def pokemon_options(pokemon_id: str, min_players: int = Query(1, ge=1)):
        result = engine.pokemon_options(
            pokemon_id.strip().lower(), TournamentFilter(min_players=min_players)
        )
        if result is None:
            raise HTTPException(404, "Pokémon not found")
        return result

    @app.post("/api/analyze")
    def analyze(query: AnalysisQuery):
        return engine.analyze(query)

    @app.post("/api/teams/search")
    def search_teams(query: TeamSearchQuery):
        return engine.search_teams(query)

    @app.post("/api/refresh")
    def refresh():
        if not refresh_lock.acquire(blocking=False):
            raise HTTPException(409, "A refresh is already running")
        try:
            return sync_database(path, raw_path)
        finally:
            refresh_lock.release()

    app.mount("/static", StaticFiles(directory=str(static_path)), name="static")
    return app
