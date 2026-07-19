export type AnalysisMode = "basic" | "versus";
export type SearchMode = "basic" | "advanced";
export type Side = "own" | "opponent";
export type DetailMode = "relative" | "full";

export interface Species {
  id: string;
  name: string;
  teams: number;
}

export interface UsageOption {
  value: string;
  teams: number;
  usage: number;
}

export interface PokemonOptions {
  id: string;
  name: string;
  teams: number;
  moves: UsageOption[];
  items: UsageOption[];
  abilities: UsageOption[];
  natures: UsageOption[];
}

export interface PokemonCondition {
  moves: string[];
  item: string | null;
  ability: string | null;
  nature: string | null;
}

export interface Health {
  status: string;
  tournaments: number;
  matches: number;
  teams: number;
}

export interface RecordSummary {
  wins: number;
  losses: number;
  ties: number;
}

export interface AnalysisResult {
  scope: { tournaments: number; matches: number };
  sample: { matches: number; tie_matches?: number };
  record: RecordSummary;
  metrics: { decisive_win_rate: number | null };
}

export interface TeamPokemon {
  id: string;
  name: string;
  item: string | null;
  ability: string | null;
  nature: string | null;
  moves: string[];
}

export interface TeamSearchResult {
  key: string;
  teams: number;
  tournaments: number;
  variants: number;
  usage: number | null;
  pokemon: TeamPokemon[];
  latest_date: string | null;
  record: RecordSummary;
  win_rate: number | null;
  source?: { placing: number | null; tournament: string | null };
}

export interface TeamSearchResponse {
  mode: SearchMode;
  total: number;
  matching_teams: number;
  results: TeamSearchResult[];
}

export type ScalarField = "item" | "ability" | "nature";

export type FieldDifference =
  | { field: ScalarField; before: string; after: string }
  | { field: "moves"; removed: string[]; added: string[] };

export interface PokemonDifference {
  id: string;
  name: string;
  fields: FieldDifference[];
}

export interface TeamDifference {
  pokemon: PokemonDifference[];
  changes: number;
}
