import { useEffect, useRef, useState } from "react";

import { api, type AnalysisRequest } from "../../api";
import { AppHeader } from "../../components/AppHeader";
import { PokemonPicker } from "../../components/PokemonPicker";
import { formatNumber } from "../../format";
import { useCatalog } from "../../hooks/useCatalog";
import { useSettings } from "../../hooks/useSettings";
import { useStoredState } from "../../hooks/useStoredState";
import type { AnalysisResult, PokemonCondition, PokemonOptions, Side } from "../../types";
import { activeTeam, conditionFor, initialAnalysisState, type AnalysisState } from "./analysisState";
import { ConditionDrawer } from "./ConditionDrawer";
import { ResultsPanel } from "./ResultsPanel";
import { TeamPanel } from "./TeamPanel";

const storageKey = "vgc-analytics-react-analysis-v1";
const sides: Side[] = ["own", "opponent"];

export function AnalysisPage() {
  const [state, setState] = useStoredState<AnalysisState>(storageKey, initialAnalysisState);
  const [settings, setSettings] = useSettings();
  const { species, imageIds, health, error: catalogError, loading, reload } = useCatalog(settings.minPlayers);
  const [pickerSide, setPickerSide] = useState<Side | null>(null);
  const [drawerPokemon, setDrawerPokemon] = useState<Record<Side, string | null>>({ own: null, opponent: null });
  const [options, setOptions] = useState<Record<string, PokemonOptions>>({});
  const [drawerErrors, setDrawerErrors] = useState<Record<string, string>>({});
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [analysisError, setAnalysisError] = useState<string | null>(null);
  const [busy, setBusy] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const sequence = useRef(0);

  const updateState = (updater: (value: AnalysisState) => AnalysisState) => setState((current) => updater(current));
  const updateSide = (side: Side, key: "teams" | "disabled" | "excludes", values: string[]) =>
    updateState((current) => ({ ...current, [key]: { ...current[key], [side]: values } }));

  useEffect(() => {
    if (!species.length) return;
    const valid = new Set(species.map((pokemon) => pokemon.id));
    updateState((current) => {
      const next = structuredClone(current);
      for (const side of sides) {
        next.teams[side] = current.teams[side].filter((id) => valid.has(id)).slice(0, 6);
        next.disabled[side] = current.disabled[side].filter((id) => next.teams[side].includes(id));
        next.excludes[side] = current.excludes[side].filter((id) => valid.has(id) && !next.teams[side].includes(id));
        next.conditions[side] = Object.fromEntries(Object.entries(current.conditions[side]).filter(([id]) => next.teams[side].includes(id)));
      }
      return JSON.stringify(next) === JSON.stringify(current) ? current : next;
    });
  }, [species, setState]);

  useEffect(() => {
    const currentSequence = ++sequence.current;
    setBusy(true);
    setAnalysisError(null);
    const timer = window.setTimeout(async () => {
      const queryConditions = (side: Side) => activeTeam(state, side).flatMap((id) => {
        const condition = conditionFor(state, side, id);
        return condition.moves.length || condition.item || condition.ability || condition.nature ? [{ pokemon_id: id, ...condition }] : [];
      });
      const versus = state.mode === "versus";
      const query: AnalysisRequest = {
        own: { contains: activeTeam(state, "own"), excludes: state.excludes.own, conditions: queryConditions("own") },
        opponent: versus
          ? { contains: activeTeam(state, "opponent"), excludes: state.excludes.opponent, conditions: queryConditions("opponent") }
          : { contains: [], excludes: [], conditions: [] },
        tournaments: { min_players: settings.minPlayers },
        mirrors: versus && state.excludeMirrors ? "exclude_own_core" : "include",
      };
      try {
        const nextResult = await api.analyze(query);
        if (sequence.current === currentSequence) setResult(nextResult);
      } catch (exception) {
        if (sequence.current === currentSequence) setAnalysisError(exception instanceof Error ? exception.message : "Could not calculate results");
      } finally {
        if (sequence.current === currentSequence) setBusy(false);
      }
    }, 180);
    return () => window.clearTimeout(timer);
  }, [settings.minPlayers, state]);

  const setMode = (mode: AnalysisState["mode"]) => {
    updateState((current) => ({ ...current, mode }));
    if (mode === "basic") setDrawerPokemon((current) => ({ ...current, opponent: null }));
  };

  const openDrawer = async (side: Side, id: string) => {
    if (drawerPokemon[side] === id) {
      setDrawerPokemon((current) => ({ ...current, [side]: null }));
      return;
    }
    setDrawerPokemon((current) => ({ ...current, [side]: id }));
    if (options[id]) return;
    try {
      const loaded = await api.pokemonOptions(id, settings.minPlayers);
      setOptions((current) => ({ ...current, [id]: loaded }));
    } catch (exception) {
      setDrawerErrors((current) => ({ ...current, [id]: exception instanceof Error ? exception.message : "Could not load conditions" }));
    }
  };

  const setCondition = (side: Side, id: string, condition: PokemonCondition) => updateState((current) => ({
    ...current,
    conditions: { ...current.conditions, [side]: { ...current.conditions[side], [id]: condition } },
  }));

  const removePokemon = (side: Side, id: string) => updateState((current) => {
    const conditions = { ...current.conditions[side] };
    delete conditions[id];
    return {
      ...current,
      teams: { ...current.teams, [side]: current.teams[side].filter((value) => value !== id) },
      disabled: { ...current.disabled, [side]: current.disabled[side].filter((value) => value !== id) },
      conditions: { ...current.conditions, [side]: conditions },
    };
  });

  const swapTeams = () => {
    setDrawerPokemon({ own: null, opponent: null });
    updateState((current) => ({
      ...current,
      teams: { own: current.teams.opponent, opponent: current.teams.own },
      disabled: { own: current.disabled.opponent, opponent: current.disabled.own },
      excludes: { own: current.excludes.opponent, opponent: current.excludes.own },
      conditions: { own: current.conditions.opponent, opponent: current.conditions.own },
    }));
  };

  const refresh = async () => {
    setRefreshing(true);
    try {
      await api.refresh();
      setOptions({});
      await reload();
    } catch (exception) {
      setAnalysisError(exception instanceof Error ? exception.message : "Could not refresh the dataset");
    } finally {
      setRefreshing(false);
    }
  };

  const teamPanel = (side: Side) => (
    <TeamPanel
      side={side}
      species={species}
      imageIds={imageIds}
      team={state.teams[side]}
      disabled={state.disabled[side]}
      excludes={state.excludes[side]}
      conditions={state.conditions[side]}
      openPokemon={drawerPokemon[side]}
      onAdd={() => setPickerSide(side)}
      onRemove={(id) => removePokemon(side, id)}
      onToggle={(id, enabled) => updateSide(side, "disabled", enabled ? state.disabled[side].filter((value) => value !== id) : [...new Set([...state.disabled[side], id])])}
      onEdit={(id) => void openDrawer(side, id)}
      onAddExclude={(id) => id && updateSide(side, "excludes", [...new Set([...state.excludes[side], id])])}
      onRemoveExclude={(id) => updateSide(side, "excludes", state.excludes[side].filter((value) => value !== id))}
    />
  );

  const emptyAnalysis = !sides.some((side) => activeTeam(state, side).length || state.excludes[side].length);
  const status = catalogError
    ?? (loading ? "Loading dataset…" : result
      ? `${formatNumber(result.scope.tournaments)} tournaments · ${formatNumber(result.scope.matches)} matches`
      : health ? `${formatNumber(health.tournaments)} tournaments · ${formatNumber(health.matches)} matches` : "Dataset unavailable");

  return (
    <>
      <AppHeader
        active="analysis"
        status={status}
        settings={settings}
        onSettingsChange={(nextSettings) => {
          if (nextSettings.minPlayers !== settings.minPlayers) setOptions({});
          setSettings(nextSettings);
        }}
        refreshing={refreshing}
        onRefresh={() => void refresh()}
        filters={state.mode === "versus" ? (
          <label className="check-row"><input type="checkbox" checked={state.excludeMirrors} onChange={(event) => updateState((current) => ({ ...current, excludeMirrors: event.target.checked }))} />Exclude mirrors</label>
        ) : undefined}
      />
      <main>
        <div className="view-header">
          <h1>Pokémon and core analysis</h1>
          <div className="view-actions">
            {state.mode === "versus" && <button id="swap-teams" type="button" aria-label="Swap your team and the opponent team" onClick={swapTeams}><span aria-hidden="true">⇄</span> Swap teams</button>}
            <div className="mode-switch" aria-label="Analysis mode">
              <button type="button" aria-pressed={state.mode === "basic"} onClick={() => setMode("basic")}>Basic</button>
              <button type="button" aria-pressed={state.mode === "versus"} onClick={() => setMode("versus")}>Versus</button>
            </div>
          </div>
        </div>
        {analysisError && <p id="error" role="alert">{analysisError}</p>}
        <div id="analysis-shell" className="analysis-shell">
          <ConditionDrawer
            side="own"
            pokemonId={drawerPokemon.own}
            species={species}
            imageIds={imageIds}
            options={drawerPokemon.own ? options[drawerPokemon.own] : undefined}
            condition={drawerPokemon.own ? conditionFor(state, "own", drawerPokemon.own) : { moves: [], item: null, ability: null, nature: null }}
            error={drawerPokemon.own ? drawerErrors[drawerPokemon.own] : null}
            onChange={(value) => drawerPokemon.own && setCondition("own", drawerPokemon.own, value)}
            onClose={() => setDrawerPokemon((current) => ({ ...current, own: null }))}
          />
          <div id="analysis-grid" className={`analysis-grid ${state.mode}`}>
            {teamPanel("own")}
            {state.mode === "versus" && <ResultsPanel result={result} busy={busy} showTies={settings.showTies} empty={emptyAnalysis} />}
            {state.mode === "versus" && teamPanel("opponent")}
            {state.mode === "basic" && <ResultsPanel result={result} busy={busy} showTies={settings.showTies} empty={emptyAnalysis} />}
          </div>
          <ConditionDrawer
            side="opponent"
            pokemonId={drawerPokemon.opponent}
            species={species}
            imageIds={imageIds}
            options={drawerPokemon.opponent ? options[drawerPokemon.opponent] : undefined}
            condition={drawerPokemon.opponent ? conditionFor(state, "opponent", drawerPokemon.opponent) : { moves: [], item: null, ability: null, nature: null }}
            error={drawerPokemon.opponent ? drawerErrors[drawerPokemon.opponent] : null}
            onChange={(value) => drawerPokemon.opponent && setCondition("opponent", drawerPokemon.opponent, value)}
            onClose={() => setDrawerPokemon((current) => ({ ...current, opponent: null }))}
          />
        </div>
      </main>
      <PokemonPicker
        open={pickerSide !== null}
        species={species}
        imageIds={imageIds}
        blocked={pickerSide ? [...state.teams[pickerSide], ...state.excludes[pickerSide]] : []}
        defaultKeepOpen={false}
        onPick={(id) => {
          if (!pickerSide) return true;
          const next = [...new Set([...state.teams[pickerSide], id])].slice(0, 6);
          updateSide(pickerSide, "teams", next);
          return next.length === 6;
        }}
        onClose={() => setPickerSide(null)}
      />
    </>
  );
}
