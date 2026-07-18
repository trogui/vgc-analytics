from __future__ import annotations

from pathlib import Path

from .database import connect


def validate_database(database_path: str | Path) -> dict[str, object]:
    with connect(database_path, read_only=True) as connection:
        columns = {
            row[1]
            for row in connection.execute("PRAGMA table_info('team_pokemon')").fetchall()
        }
        counts = connection.execute("""
            SELECT
                (SELECT COUNT(*) FROM tournaments),
                (SELECT COUNT(*) FROM entries),
                (SELECT COUNT(*) FROM teams),
                (SELECT COUNT(*) FROM matches),
                (SELECT COUNT(*) FROM match_sides),
                (SELECT COUNT(*) FROM data_quality_issues)
        """).fetchone()
        wrong_team_sizes = connection.execute("""
            SELECT COUNT(*) FROM (
                SELECT entry_id FROM team_pokemon GROUP BY entry_id HAVING COUNT(*) <> 6
            )
        """).fetchone()[0]
        wins, losses, ties, effective_rate = connection.execute("""
            SELECT count_if(outcome='W'), count_if(outcome='L'), count_if(outcome='T'),
                   SUM(score) / COUNT(*)
            FROM match_sides WHERE competitive
        """).fetchone()
        orphan_sides = connection.execute("""
            SELECT COUNT(*)
            FROM match_sides ms
            LEFT JOIN teams own_team ON own_team.entry_id = ms.own_entry_id
            LEFT JOIN teams opponent_team ON opponent_team.entry_id = ms.opponent_entry_id
            WHERE ms.analyzable AND (own_team.entry_id IS NULL OR opponent_team.entry_id IS NULL)
        """).fetchone()[0]
        formats = connection.execute(
            "SELECT list(DISTINCT game), list(DISTINCT format) FROM tournaments"
        ).fetchone()

    checks = {
        "tera_absent": "tera" not in columns,
        "all_valid_teams_have_six_pokemon": wrong_team_sizes == 0,
        "wins_equal_losses": wins == losses,
        "ties_have_two_sides": ties % 2 == 0,
        "global_effective_win_rate_is_50_percent": abs(effective_rate - 0.5) < 1e-12,
        "competitive_sides_have_two_valid_teams": orphan_sides == 0,
        "only_vgc_mb": formats == (["VGC"], ["M-B"]),
    }
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise ValueError(f"Database validation failed: {', '.join(failed)}")
    return {
        "valid": True,
        "checks": checks,
        "counts": {
            "tournaments": counts[0],
            "entries": counts[1],
            "valid_teams": counts[2],
            "matches": counts[3],
            "match_sides": counts[4],
            "quality_issues": counts[5],
        },
    }
