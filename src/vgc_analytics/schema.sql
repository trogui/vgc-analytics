CREATE TABLE IF NOT EXISTS tournaments (
    tournament_id VARCHAR PRIMARY KEY,
    name VARCHAR NOT NULL,
    tournament_date TIMESTAMPTZ NOT NULL,
    game VARCHAR NOT NULL,
    format VARCHAR NOT NULL,
    listed_players INTEGER NOT NULL,
    source_hash VARCHAR NOT NULL
);

CREATE TABLE IF NOT EXISTS entries (
    entry_id VARCHAR PRIMARY KEY,
    tournament_id VARCHAR NOT NULL,
    player_id VARCHAR NOT NULL,
    final_placing INTEGER,
    wins INTEGER,
    losses INTEGER,
    ties INTEGER,
    has_teamlist BOOLEAN NOT NULL,
    teamlist_valid BOOLEAN NOT NULL
);

CREATE TABLE IF NOT EXISTS teams (
    entry_id VARCHAR PRIMARY KEY,
    composition_key VARCHAR NOT NULL,
    open_sheet_key VARCHAR NOT NULL
);

CREATE TABLE IF NOT EXISTS team_pokemon (
    entry_id VARCHAR NOT NULL,
    slot SMALLINT NOT NULL,
    pokemon_id VARCHAR NOT NULL,
    pokemon_name VARCHAR NOT NULL,
    item VARCHAR,
    ability VARCHAR,
    nature VARCHAR,
    PRIMARY KEY (entry_id, slot)
);

CREATE TABLE IF NOT EXISTS team_moves (
    entry_id VARCHAR NOT NULL,
    pokemon_slot SMALLINT NOT NULL,
    move_slot SMALLINT NOT NULL,
    move VARCHAR NOT NULL,
    PRIMARY KEY (entry_id, pokemon_slot, move_slot)
);

CREATE TABLE IF NOT EXISTS matches (
    match_id VARCHAR PRIMARY KEY,
    tournament_id VARCHAR NOT NULL,
    phase INTEGER,
    round INTEGER,
    table_number INTEGER,
    match_label VARCHAR,
    player1_entry_id VARCHAR,
    player2_entry_id VARCHAR,
    winner_entry_id VARCHAR,
    status VARCHAR NOT NULL
);

CREATE TABLE IF NOT EXISTS match_sides (
    match_id VARCHAR NOT NULL,
    side SMALLINT NOT NULL,
    tournament_id VARCHAR NOT NULL,
    own_entry_id VARCHAR NOT NULL,
    opponent_entry_id VARCHAR NOT NULL,
    outcome VARCHAR NOT NULL,
    score DOUBLE NOT NULL,
    competitive BOOLEAN NOT NULL,
    analyzable BOOLEAN NOT NULL,
    PRIMARY KEY (match_id, side)
);

CREATE TABLE IF NOT EXISTS ingestion_log (
    tournament_id VARCHAR PRIMARY KEY,
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT current_timestamp,
    source_hash VARCHAR NOT NULL
);

CREATE TABLE IF NOT EXISTS data_quality_issues (
    issue_id VARCHAR PRIMARY KEY,
    tournament_id VARCHAR NOT NULL,
    entry_id VARCHAR,
    code VARCHAR NOT NULL,
    detail VARCHAR NOT NULL
);

CREATE INDEX IF NOT EXISTS entries_tournament_idx ON entries(tournament_id);
CREATE INDEX IF NOT EXISTS team_pokemon_species_idx ON team_pokemon(pokemon_id, entry_id);
CREATE INDEX IF NOT EXISTS match_sides_own_idx ON match_sides(own_entry_id);
CREATE INDEX IF NOT EXISTS match_sides_opponent_idx ON match_sides(opponent_entry_id);
CREATE INDEX IF NOT EXISTS tournaments_filter_idx ON tournaments(listed_players, tournament_date);
