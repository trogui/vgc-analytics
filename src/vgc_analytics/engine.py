from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, model_validator

from .database import connect
from .ingest import core_key


class PokemonCondition(BaseModel):
    pokemon_id: str
    moves: list[str] = Field(default_factory=list, max_length=4)
    item: str | None = None
    ability: str | None = None

    @model_validator(mode="after")
    def normalize(self):
        self.pokemon_id = self.pokemon_id.strip().lower()
        self.moves = sorted({value.strip() for value in self.moves if value.strip()})
        self.item = self.item.strip() if self.item and self.item.strip() else None
        self.ability = self.ability.strip() if self.ability and self.ability.strip() else None
        return self


class TeamFilter(BaseModel):
    contains: list[str] = Field(default_factory=list, max_length=6)
    excludes: list[str] = Field(default_factory=list, max_length=6)
    conditions: list[PokemonCondition] = Field(default_factory=list, max_length=6)
    exact: bool = False

    @model_validator(mode="after")
    def normalize_and_validate(self):
        self.contains = list(dict.fromkeys(value.strip().lower() for value in self.contains if value.strip()))
        self.excludes = sorted({value.strip().lower() for value in self.excludes if value.strip()})
        overlap = set(self.contains) & set(self.excludes)
        if overlap:
            raise ValueError(f"Pokémon both included and excluded: {', '.join(sorted(overlap))}")
        if self.exact and len(self.contains) != 6:
            raise ValueError("An exact team must contain exactly six Pokémon")
        condition_species = [condition.pokemon_id for condition in self.conditions]
        if len(condition_species) != len(set(condition_species)):
            raise ValueError("Only one condition set is allowed per Pokémon")
        return self


class TournamentFilter(BaseModel):
    min_players: int = Field(default=1, ge=1)


class AnalysisQuery(BaseModel):
    own: TeamFilter = Field(default_factory=TeamFilter)
    opponent: TeamFilter = Field(default_factory=TeamFilter)
    tournaments: TournamentFilter = Field(default_factory=TournamentFilter)
    mirrors: Literal["include", "exclude_own_core"] = "include"


class TeamSearchQuery(BaseModel):
    mode: Literal["basic", "advanced"] = "basic"
    team: TeamFilter
    tournaments: TournamentFilter = Field(default_factory=TournamentFilter)
    limit: int = Field(default=50, ge=1, le=50)

    @model_validator(mode="after")
    def validate_search(self):
        if not self.team.contains:
            raise ValueError("Select at least one Pokémon")
        condition_species = {condition.pokemon_id for condition in self.team.conditions}
        if not condition_species <= set(self.team.contains):
            raise ValueError("Conditions can only target selected Pokémon")
        if self.mode == "basic" and self.team.conditions:
            raise ValueError("Set conditions require advanced search")
        self.team.exact = len(self.team.contains) == 6
        return self


def _in_clause(values: list[str], parameters: list[object]) -> str:
    parameters.extend(values)
    return ",".join("?" for _ in values)


def _team_conditions(alias: str, team_filter: TeamFilter, parameters: list[object]) -> list[str]:
    conditions: list[str] = []
    if team_filter.contains:
        if team_filter.exact:
            conditions.append(
                f"EXISTS (SELECT 1 FROM teams filter_team WHERE filter_team.entry_id = {alias} AND filter_team.composition_key = ?)"
            )
            parameters.append(core_key(team_filter.contains))
        else:
            placeholders = _in_clause(team_filter.contains, parameters)
            conditions.append(f"""
                (SELECT COUNT(*) FROM team_pokemon included
                 WHERE included.entry_id = {alias}
                   AND included.pokemon_id IN ({placeholders})) = ?
            """)
            parameters.append(len(team_filter.contains))
    if team_filter.excludes:
        placeholders = _in_clause(team_filter.excludes, parameters)
        conditions.append(
            f"NOT EXISTS (SELECT 1 FROM team_pokemon excluded WHERE excluded.entry_id = {alias} AND excluded.pokemon_id IN ({placeholders}))"
        )
    for index, pokemon in enumerate(team_filter.conditions):
        pokemon_alias = f"condition_pokemon_{index}"
        pokemon_conditions = [
            f"{pokemon_alias}.entry_id = {alias}",
            f"{pokemon_alias}.pokemon_id = ?",
        ]
        parameters.append(pokemon.pokemon_id)
        if pokemon.item:
            pokemon_conditions.append(f"lower({pokemon_alias}.item) = lower(?)")
            parameters.append(pokemon.item)
        if pokemon.ability:
            pokemon_conditions.append(f"lower({pokemon_alias}.ability) = lower(?)")
            parameters.append(pokemon.ability)
        for move in pokemon.moves:
            pokemon_conditions.append(f"""
                EXISTS (
                    SELECT 1 FROM team_moves condition_move
                    WHERE condition_move.entry_id = {pokemon_alias}.entry_id
                      AND condition_move.pokemon_slot = {pokemon_alias}.slot
                      AND lower(condition_move.move) = lower(?)
                )
            """)
            parameters.append(move)
        conditions.append(f"EXISTS (SELECT 1 FROM team_pokemon {pokemon_alias} WHERE {' AND '.join(pokemon_conditions)})")
    return conditions


def _tournament_conditions(filters: TournamentFilter, parameters: list[object]) -> list[str]:
    parameters.append(filters.min_players)
    return ["t.listed_players >= ?"]


class AnalyticsEngine:
    def __init__(self, database_path: str | Path):
        self.database_path = Path(database_path)

    def species(self, filters: TournamentFilter | None = None) -> list[dict[str, object]]:
        filters = filters or TournamentFilter()
        parameters: list[object] = []
        tournament_conditions = _tournament_conditions(filters, parameters)
        with connect(self.database_path, read_only=True) as connection:
            rows = connection.execute(f"""
                SELECT tp.pokemon_id, any_value(tp.pokemon_name) AS pokemon_name,
                       COUNT(DISTINCT tp.entry_id) AS teams
                FROM team_pokemon tp
                JOIN entries e USING (entry_id)
                JOIN tournaments t USING (tournament_id)
                WHERE EXISTS (
                    SELECT 1 FROM match_sides ms
                    WHERE ms.own_entry_id = tp.entry_id
                      AND ms.competitive AND ms.analyzable
                )
                  AND {' AND '.join(f'({value})' for value in tournament_conditions)}
                GROUP BY tp.pokemon_id
                ORDER BY teams DESC, pokemon_name
            """, parameters).fetchall()
        return [
            {"id": pokemon_id, "name": name, "teams": teams}
            for pokemon_id, name, teams in rows
        ]

    def pokemon_options(self, pokemon_id: str, filters: TournamentFilter | None = None) -> dict[str, object] | None:
        filters = filters or TournamentFilter()
        filter_parameters: list[object] = []
        tournament_conditions = _tournament_conditions(filters, filter_parameters)
        eligible_pokemon = f"""
            SELECT tp.*
            FROM team_pokemon tp
            JOIN entries e USING (entry_id)
            JOIN tournaments t USING (tournament_id)
            WHERE EXISTS (
                SELECT 1 FROM match_sides ms
                WHERE ms.own_entry_id = tp.entry_id
                  AND ms.competitive AND ms.analyzable
            )
              AND {' AND '.join(f'({value})' for value in tournament_conditions)}
        """
        with connect(self.database_path, read_only=True) as connection:
            pokemon = connection.execute(f"""
                WITH eligible_pokemon AS ({eligible_pokemon})
                SELECT any_value(pokemon_name), COUNT(DISTINCT entry_id)
                FROM eligible_pokemon
                WHERE pokemon_id = ?
            """, [*filter_parameters, pokemon_id]).fetchone()
            if not pokemon or not pokemon[1]:
                return None
            name, teams = pokemon
            moves = connection.execute(f"""
                WITH eligible_pokemon AS ({eligible_pokemon}),
                variants AS (
                    SELECT lower(trim(tm.move)) AS normalized, tm.move AS value,
                           COUNT(DISTINCT tp.entry_id) AS teams
                    FROM eligible_pokemon tp
                    JOIN team_moves tm ON tm.entry_id = tp.entry_id AND tm.pokemon_slot = tp.slot
                    WHERE tp.pokemon_id = ?
                    GROUP BY normalized, value
                )
                SELECT arg_max(value, teams), SUM(teams) AS teams
                FROM variants
                GROUP BY normalized
                HAVING teams >= ?
                ORDER BY teams DESC, arg_max(value, teams)
                LIMIT 20
            """, [*filter_parameters, pokemon_id, max(2, round(teams * 0.001))]).fetchall()
            items = connection.execute(f"""
                WITH eligible_pokemon AS ({eligible_pokemon}),
                variants AS (
                    SELECT lower(trim(item)) AS normalized, item AS value,
                           COUNT(DISTINCT entry_id) AS teams
                    FROM eligible_pokemon
                    WHERE pokemon_id = ? AND item IS NOT NULL AND item != ''
                    GROUP BY normalized, value
                )
                SELECT arg_max(value, teams), SUM(teams) AS teams
                FROM variants
                GROUP BY normalized
                HAVING teams >= ?
                ORDER BY teams DESC, arg_max(value, teams)
                LIMIT 15
            """, [*filter_parameters, pokemon_id, max(2, round(teams * 0.001))]).fetchall()
            abilities = connection.execute(f"""
                WITH eligible_pokemon AS ({eligible_pokemon}),
                variants AS (
                    SELECT lower(trim(ability)) AS normalized, ability AS value,
                           COUNT(DISTINCT entry_id) AS teams
                    FROM eligible_pokemon
                    WHERE pokemon_id = ? AND ability IS NOT NULL AND ability != ''
                    GROUP BY normalized, value
                )
                SELECT arg_max(value, teams), SUM(teams) AS teams
                FROM variants
                GROUP BY normalized
                HAVING teams >= ?
                ORDER BY teams DESC, arg_max(value, teams)
                LIMIT 10
            """, [*filter_parameters, pokemon_id, max(2, round(teams * 0.001))]).fetchall()

        def values(rows):
            return [
                {"value": value, "teams": count, "usage": count / teams}
                for value, count in rows
            ]

        return {
            "id": pokemon_id,
            "name": name,
            "teams": teams,
            "moves": values(moves),
            "items": values(items),
            "abilities": values(abilities),
        }

    def search_teams(self, query: TeamSearchQuery) -> dict[str, object]:
        parameters: list[object] = []
        conditions = ["e.teamlist_valid"]
        conditions.extend(_team_conditions("e.entry_id", query.team, parameters))
        conditions.extend(_tournament_conditions(query.tournaments, parameters))
        group_column = "composition_key" if query.mode == "basic" else "open_sheet_key"
        eligible = f"""
            SELECT team.entry_id, team.composition_key, team.open_sheet_key,
                   e.player_name, e.final_placing,
                   t.tournament_id, t.name AS tournament_name,
                   CAST(t.tournament_date AS DATE) AS tournament_date
            FROM teams team
            JOIN entries e USING (entry_id)
            JOIN tournaments t USING (tournament_id)
            WHERE {' AND '.join(f'({condition})' for condition in conditions)}
        """
        sql = f"""
            WITH eligible AS ({eligible}),
            ranked AS (
                SELECT {group_column} AS result_key,
                       COUNT(*) AS occurrences,
                       COUNT(DISTINCT tournament_id) AS tournaments,
                       COUNT(DISTINCT open_sheet_key) AS variants,
                       MAX(tournament_date) AS latest_date,
                       arg_max(entry_id, tournament_date) AS representative_entry_id,
                       COUNT(*) OVER () AS total_results,
                       SUM(COUNT(*)) OVER () AS matching_teams
                FROM eligible
                GROUP BY {group_column}
                ORDER BY occurrences DESC, latest_date DESC, result_key
                LIMIT ?
            ),
            records AS (
                SELECT eligible.{group_column} AS result_key,
                       count_if(ms.outcome = 'W') AS wins,
                       count_if(ms.outcome = 'L') AS losses,
                       count_if(ms.outcome = 'T') AS ties
                FROM eligible
                JOIN match_sides ms ON ms.own_entry_id = eligible.entry_id
                WHERE ms.competitive AND ms.analyzable
                GROUP BY eligible.{group_column}
            )
            SELECT ranked.*, eligible.player_name, eligible.final_placing,
                   eligible.tournament_name, records.wins, records.losses, records.ties
            FROM ranked
            JOIN eligible ON eligible.entry_id = ranked.representative_entry_id
            LEFT JOIN records USING (result_key)
            ORDER BY occurrences DESC, latest_date DESC, result_key
        """
        with connect(self.database_path, read_only=True) as connection:
            rows = connection.execute(sql, [*parameters, query.limit]).fetchall()
            representative_ids = [row[5] for row in rows]
            team_rows = []
            if representative_ids:
                detail_parameters: list[object] = []
                placeholders = _in_clause(representative_ids, detail_parameters)
                team_rows = connection.execute(f"""
                    SELECT tp.entry_id, tp.slot, tp.pokemon_id, tp.pokemon_name,
                           tp.item, tp.ability, tp.nature,
                           list(tm.move ORDER BY tm.move_slot)
                               FILTER (WHERE tm.move IS NOT NULL) AS moves
                    FROM team_pokemon tp
                    LEFT JOIN team_moves tm
                      ON tm.entry_id = tp.entry_id AND tm.pokemon_slot = tp.slot
                    WHERE tp.entry_id IN ({placeholders})
                    GROUP BY tp.entry_id, tp.slot, tp.pokemon_id, tp.pokemon_name,
                             tp.item, tp.ability, tp.nature
                    ORDER BY tp.entry_id, tp.slot
                """, detail_parameters).fetchall()

        members: dict[str, list[dict[str, object]]] = {}
        for entry_id, _, pokemon_id, name, item, ability, nature, moves in team_rows:
            members.setdefault(entry_id, []).append({
                "id": pokemon_id,
                "name": name,
                "item": item,
                "ability": ability,
                "nature": nature,
                "moves": moves or [],
            })

        requested_order = {pokemon_id: index for index, pokemon_id in enumerate(query.team.contains)}
        for pokemon in members.values():
            pokemon.sort(key=lambda value: (
                requested_order.get(value["id"], len(requested_order)),
                value["name"],
            ))

        results = []
        for key, occurrences, tournaments, variants, latest_date, entry_id, _, matching_teams, player_name, placing, tournament_name, wins, losses, ties in rows:
            wins, losses, ties = wins or 0, losses or 0, ties or 0
            decisive = wins + losses
            result = {
                "key": key,
                "teams": occurrences,
                "tournaments": tournaments,
                "variants": variants,
                "usage": occurrences / matching_teams if matching_teams else None,
                "pokemon": members.get(entry_id, []),
                "latest_date": str(latest_date) if latest_date else None,
                "record": {"wins": wins, "losses": losses, "ties": ties},
                "win_rate": wins / decisive if decisive else None,
            }
            if query.mode == "advanced":
                result["source"] = {
                    "player": player_name,
                    "placing": placing,
                    "tournament": tournament_name,
                }
            results.append(result)
        return {
            "mode": query.mode,
            "total": rows[0][6] if rows else 0,
            "matching_teams": rows[0][7] if rows else 0,
            "results": results,
        }

    def analyze(self, query: AnalysisQuery) -> dict[str, object]:
        parameters: list[object] = []
        conditions = [
            "ms.competitive",
            "ms.analyzable",
        ]
        conditions.extend(_team_conditions("ms.own_entry_id", query.own, parameters))
        conditions.extend(_team_conditions("ms.opponent_entry_id", query.opponent, parameters))
        conditions.extend(_tournament_conditions(query.tournaments, parameters))
        if query.mirrors == "exclude_own_core" and query.own.contains:
            placeholders = _in_clause(query.own.contains, parameters)
            conditions.append(f"""
                (SELECT COUNT(*) FROM team_pokemon mirror
                 WHERE mirror.entry_id = ms.opponent_entry_id
                   AND mirror.pokemon_id IN ({placeholders})) < ?
            """)
            parameters.append(len(query.own.contains))

        where = " AND ".join(f"({condition})" for condition in conditions)
        sql = f"""
            SELECT COUNT(*),
                   count_if(ms.outcome = 'W'),
                   count_if(ms.outcome = 'L'),
                   count_if(ms.outcome = 'T')
            FROM match_sides ms
            JOIN tournaments t USING (tournament_id)
            WHERE {where}
        """
        with connect(self.database_path, read_only=True) as connection:
            matches, wins, losses, ties = connection.execute(sql, parameters).fetchone()
            scope_parameters: list[object] = []
            scope_conditions = ["ms.competitive", "ms.analyzable"]
            scope_conditions.extend(_tournament_conditions(query.tournaments, scope_parameters))
            scope_tournaments, scope_matches = connection.execute(f"""
                SELECT COUNT(DISTINCT ms.tournament_id), COUNT(DISTINCT ms.match_id)
                FROM match_sides ms
                JOIN tournaments t USING (tournament_id)
                WHERE {' AND '.join(f'({value})' for value in scope_conditions)}
            """, scope_parameters).fetchone()

        wins, losses, ties = wins or 0, losses or 0, ties or 0
        decisive = wins + losses
        return {
            "scope": {"tournaments": scope_tournaments, "matches": scope_matches},
            "sample": {"matches": matches},
            "record": {"wins": wins, "losses": losses, "ties": ties},
            "metrics": {"decisive_win_rate": wins / decisive if decisive else None},
        }
