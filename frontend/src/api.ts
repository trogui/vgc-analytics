import type {
  AnalysisResult,
  Health,
  PokemonCondition,
  PokemonOptions,
  SearchMode,
  Species,
  TeamSearchResponse,
} from "./types";

interface TeamQuery {
  contains: string[];
  excludes?: string[];
  conditions?: Array<PokemonCondition & { pokemon_id: string }>;
}

export interface AnalysisRequest {
  own: TeamQuery;
  opponent: TeamQuery;
  tournaments: { min_players: number };
  mirrors: "include" | "exclude_own_core";
}

export interface TeamSearchRequest {
  mode: SearchMode;
  team: TeamQuery;
  tournaments: { min_players: number };
}

async function request<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, init);
  if (!response.ok) {
    let message = response.statusText || "Request failed";
    try {
      const body = await response.json() as { detail?: string };
      if (body.detail) message = body.detail;
    } catch {
      // The server did not return JSON.
    }
    throw new Error(message);
  }
  return response.json() as Promise<T>;
}

const jsonPost = <T>(url: string, body?: unknown) => request<T>(url, {
  method: "POST",
  headers: body === undefined ? undefined : { "Content-Type": "application/json" },
  body: body === undefined ? undefined : JSON.stringify(body),
});

export const api = {
  health: () => request<Health>("/api/health"),
  species: (minPlayers: number) => request<Species[]>(`/api/species?min_players=${minPlayers}`),
  pokemonOptions: (id: string, minPlayers: number) =>
    request<PokemonOptions>(`/api/species/${encodeURIComponent(id)}/options?min_players=${minPlayers}`),
  pokemonImages: () => request<Record<string, number>>(`${import.meta.env.BASE_URL}pokemon-images.json`),
  analyze: (query: AnalysisRequest) => jsonPost<AnalysisResult>("/api/analyze", query),
  searchTeams: (query: TeamSearchRequest) => jsonPost<TeamSearchResponse>("/api/teams/search", query),
  refresh: () => jsonPost<Record<string, unknown>>("/api/refresh"),
};
