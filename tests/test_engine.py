from __future__ import annotations

from itertools import product

import pytest

from vgc_analytics.database import connect
from vgc_analytics.engine import (
    AnalysisQuery,
    AnalyticsEngine,
    TeamFilter,
    TeamSearchQuery,
    TournamentFilter,
)
from vgc_analytics.ingest import core_key, ingest_payload
from vgc_analytics.validate import validate_database

from conftest import TEAM_A, payload, standing


def test_basculegion_overall(database):
    result = AnalyticsEngine(database).analyze(
        AnalysisQuery(own=TeamFilter(contains=["basculegion"]))
    )
    assert result["record"] == {"wins": 2, "losses": 2, "ties": 1}
    assert result["sample"] == {"matches": 4, "tie_matches": 1}
    assert result["metrics"]["decisive_win_rate"] == 0.5


def test_large_tournaments_and_mirror_exclusion(database):
    engine = AnalyticsEngine(database)
    large_only = AnalysisQuery(
        own=TeamFilter(contains=["basculegion"]),
        tournaments=TournamentFilter(min_players=21),
    )
    result = engine.analyze(large_only)
    assert result["record"] == {"wins": 2, "losses": 1, "ties": 1}
    assert result["metrics"]["decisive_win_rate"] == pytest.approx(2 / 3)

    without_mirrors = engine.analyze(large_only.model_copy(update={"mirrors": "exclude_own_core"}))
    assert without_mirrors["record"] == {"wins": 1, "losses": 0, "ties": 1}
    assert without_mirrors["sample"]["matches"] == 2
    assert without_mirrors["metrics"]["decisive_win_rate"] == 1.0


def test_core_against_core(database):
    result = AnalyticsEngine(database).analyze(AnalysisQuery(
        own=TeamFilter(contains=["basculegion", "sneasler", "kingambit"]),
        opponent=TeamFilter(contains=["tyranitar", "excadrill"]),
        tournaments=TournamentFilter(min_players=21),
    ))
    assert result["record"] == {"wins": 1, "losses": 0, "ties": 0}
    assert result["sample"]["matches"] == 1


def test_swapping_sides_preserves_samples_and_reverses_outcomes(database):
    engine = AnalyticsEngine(database)
    filters = [
        TeamFilter(),
        TeamFilter(contains=["basculegion"]),
        TeamFilter(contains=["tyranitar", "excadrill"]),
        TeamFilter(contains=["charizard"], excludes=["basculegion"]),
        TeamFilter(
            contains=["basculegion"],
            conditions=[{
                "pokemon_id": "basculegion",
                "moves": ["Protect"],
                "item": "Basculegionite",
                "ability": "Test Ability",
            }],
        ),
    ]
    for own, opponent, mirrors, min_players in product(
        filters, filters, ("include", "exclude_own_core"), (1, 21),
    ):
        query = AnalysisQuery(
            own=own,
            opponent=opponent,
            mirrors=mirrors,
            tournaments=TournamentFilter(min_players=min_players),
        )
        swapped = query.model_copy(update={"own": opponent, "opponent": own})
        result = engine.analyze(query)
        inverse = engine.analyze(swapped)
        context = query.model_dump()

        assert result["scope"] == inverse["scope"], context
        assert result["sample"] == inverse["sample"], context
        assert result["sample"]["matches"] <= result["scope"]["matches"], context
        assert result["sample"]["tie_matches"] <= result["sample"]["matches"], context
        assert result["sample"]["tie_matches"] <= result["record"]["ties"] <= 2 * result["sample"]["tie_matches"], context
        assert sum(result["record"].values()) <= 2 * result["sample"]["matches"], context
        assert result["record"] == {
            "wins": inverse["record"]["losses"],
            "losses": inverse["record"]["wins"],
            "ties": inverse["record"]["ties"],
        }, context
        win_rate = result["metrics"]["decisive_win_rate"]
        inverse_win_rate = inverse["metrics"]["decisive_win_rate"]
        decisive = result["record"]["wins"] + result["record"]["losses"]
        if win_rate is None:
            assert decisive == 0 and inverse_win_rate is None, context
        else:
            assert win_rate == pytest.approx(result["record"]["wins"] / decisive), context
            assert win_rate + inverse_win_rate == pytest.approx(1), context


def test_basic_team_search_returns_six_pokemon_compositions(database):
    result = AnalyticsEngine(database).search_teams(TeamSearchQuery(
        mode="basic",
        team=TeamFilter(contains=["basculegion"]),
        tournaments=TournamentFilter(min_players=21),
    ))
    assert result["total"] == 2
    assert result["matching_teams"] == 2
    assert all(len(row["pokemon"]) == 6 for row in result["results"])
    assert all("basculegion" in {pokemon["id"] for pokemon in row["pokemon"]} for row in result["results"])
    assert all(row["pokemon"][0]["id"] == "basculegion" for row in result["results"])
    assert {
        (row["record"]["wins"], row["record"]["losses"], row["record"]["ties"])
        for row in result["results"]
    } == {(1, 1, 0), (1, 0, 1)}
    assert {row["win_rate"] for row in result["results"]} == {0.5, 1.0}


def test_six_pokemon_search_is_exact_and_advanced_returns_sets(database):
    engine = AnalyticsEngine(database)
    exact = engine.search_teams(TeamSearchQuery(
        mode="basic",
        team=TeamFilter(contains=TEAM_A),
    ))
    assert exact["total"] == 1
    assert exact["results"][0]["teams"] == 1
    assert [pokemon["id"] for pokemon in exact["results"][0]["pokemon"]] == TEAM_A

    advanced = engine.search_teams(TeamSearchQuery(
        mode="advanced",
        team=TeamFilter(
            contains=["basculegion"],
            conditions=[{
                "pokemon_id": "basculegion",
                "moves": ["Protect"],
                "item": "Basculegionite",
                "ability": "Test Ability",
            }],
        ),
    ))
    assert advanced["total"] == 2
    assert advanced["results"][0]["pokemon"][0]["moves"] == ["Protect", "Test Move"]
    assert advanced["results"][0]["source"]["tournament"] in {"large", "small"}
    assert advanced["results"][0]["record"] == {"wins": 1, "losses": 1, "ties": 1}


def test_tera_is_absent(database):
    with connect(database, read_only=True) as connection:
        columns = {row[1] for row in connection.execute("PRAGMA table_info('team_pokemon')").fetchall()}
        item = connection.execute("""
            SELECT item FROM team_pokemon
            WHERE pokemon_id = 'basculegion' AND item IS NOT NULL
            LIMIT 1
        """).fetchone()[0]
    assert "tera" not in columns
    assert item == "Basculegionite"


def test_core_keys_are_order_independent():
    assert core_key(["sneasler", "basculegion", "kingambit"]) == core_key(
        ["kingambit", "sneasler", "basculegion"]
    )


def test_double_losses_byes_and_unknown_teams_are_excluded(database):
    result = AnalyticsEngine(database).analyze(AnalysisQuery())
    assert result["sample"] == {"matches": 4, "tie_matches": 1}
    assert result["record"] == {"wins": 3, "losses": 3, "ties": 2}


def test_idempotent_ingestion(database):
    duplicate = payload(
        "large",
        24,
        [standing("a", TEAM_A, 1)],
        [],
    )
    with connect(database) as connection:
        before = connection.execute("SELECT COUNT(*) FROM tournaments").fetchone()[0]
        assert ingest_payload(connection, duplicate) is False
        after = connection.execute("SELECT COUNT(*) FROM tournaments").fetchone()[0]
    assert before == after


def test_invalid_filters_are_rejected():
    with pytest.raises(ValueError):
        TeamFilter(contains=["basculegion"], excludes=["basculegion"])
    with pytest.raises(ValueError):
        TeamFilter(contains=["basculegion"], exact=True)
    with pytest.raises(ValueError):
        TeamSearchQuery(mode="basic", team=TeamFilter())
    with pytest.raises(ValueError):
        TeamSearchQuery(
            mode="advanced",
            team=TeamFilter(
                contains=["sneasler"],
                conditions=[{"pokemon_id": "basculegion"}],
            ),
        )


def test_invalid_source_team_is_retained_but_excluded(database):
    invalid_team = TEAM_A.copy()
    invalid_team[5] = invalid_team[0]
    invalid = payload(
        "invalid-source",
        20,
        [standing("bad", invalid_team, 1)],
        [],
    )
    with connect(database) as connection:
        assert ingest_payload(connection, invalid)
        entry = connection.execute("""
            SELECT has_teamlist, teamlist_valid FROM entries
            WHERE tournament_id = 'invalid-source'
        """).fetchone()
        issue = connection.execute("""
            SELECT code FROM data_quality_issues
            WHERE tournament_id = 'invalid-source'
        """).fetchone()[0]
        team_count = connection.execute("""
            SELECT COUNT(*) FROM teams WHERE entry_id LIKE 'invalid-source:%'
        """).fetchone()[0]
    assert entry == (True, False)
    assert issue == "duplicate_species"
    assert team_count == 0


def test_database_invariants(database):
    result = validate_database(database)
    assert result["valid"] is True
    assert all(result["checks"].values())
