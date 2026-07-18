import type { AnalysisMode, PokemonCondition, Side } from "../../types";

export interface AnalysisState {
  mode: AnalysisMode;
  teams: Record<Side, string[]>;
  disabled: Record<Side, string[]>;
  excludes: Record<Side, string[]>;
  conditions: Record<Side, Record<string, PokemonCondition>>;
  excludeMirrors: boolean;
}

export const emptyCondition = (): PokemonCondition => ({ moves: [], item: null, ability: null });

export const initialAnalysisState: AnalysisState = {
  mode: "basic",
  teams: { own: [], opponent: [] },
  disabled: { own: [], opponent: [] },
  excludes: { own: [], opponent: [] },
  conditions: { own: {}, opponent: {} },
  excludeMirrors: false,
};

export function conditionFor(state: AnalysisState, side: Side, id: string) {
  return state.conditions[side][id] ?? emptyCondition();
}

export function activeTeam(state: AnalysisState, side: Side) {
  return state.teams[side].filter((id) => !state.disabled[side].includes(id));
}
