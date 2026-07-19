import { useEffect, useState } from "react";

import { api } from "../../api";
import { AppHeader } from "../../components/AppHeader";
import { PokemonPicker } from "../../components/PokemonPicker";
import { PokemonSprite } from "../../components/PokemonSprite";
import { formatNumber } from "../../format";
import { useCatalog } from "../../hooks/useCatalog";
import { useSettings } from "../../hooks/useSettings";
import { useStoredState } from "../../hooks/useStoredState";
import type { DetailMode, PokemonCondition, PokemonOptions, SearchMode, TeamSearchResponse, TeamSearchResult } from "../../types";
import { ConditionDialog } from "./ConditionDialog";
import { TeamResults } from "./TeamResults";

interface StoredState {
  mode: SearchMode;
  selected: string[];
  conditions: Record<string, PokemonCondition>;
}

const storageKey = "vgc-analytics-react-teams-v1";
const initialState: StoredState = { mode: "basic", selected: [], conditions: {} };
const emptyCondition = (): PokemonCondition => ({ moves: [], item: null, ability: null, nature: null });

export function TeamsPage() {
  const [state, setState] = useStoredState<StoredState>(storageKey, initialState);
  const [settings, setSettings] = useSettings();
  const { species, imageIds, health, error: catalogError, loading } = useCatalog(settings.minPlayers);
  const [pickerOpen, setPickerOpen] = useState(false);
  const [editing, setEditing] = useState<string | null>(null);
  const [options, setOptions] = useState<Record<string, PokemonOptions>>({});
  const [optionErrors, setOptionErrors] = useState<Record<string, string>>({});
  const [result, setResult] = useState<TeamSearchResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [searching, setSearching] = useState(false);
  const [expanded, setExpanded] = useState<Set<number>>(new Set());
  const [referenceKey, setReferenceKey] = useState<string | null>(null);
  const [detailMode, setDetailMode] = useState<DetailMode>("relative");

  useEffect(() => {
    if (!species.length) return;
    const valid = new Set(species.map((pokemon) => pokemon.id));
    setState((current) => {
      const selected = current.selected.filter((id) => valid.has(id)).slice(0, 6);
      const conditions = Object.fromEntries(Object.entries(current.conditions).filter(([id]) => selected.includes(id)));
      return selected.length === current.selected.length && Object.keys(conditions).length === Object.keys(current.conditions).length
        ? current
        : { ...current, selected, conditions };
    });
  }, [setState, species]);

  const setMode = (mode: SearchMode) => {
    setState((current) => ({ ...current, mode }));
    setResult(null);
    setExpanded(new Set());
    setReferenceKey(null);
  };

  const openConditions = async (id: string) => {
    setEditing(id);
    if (options[id]) return;
    try {
      const loaded = await api.pokemonOptions(id, settings.minPlayers);
      setOptions((current) => ({ ...current, [id]: loaded }));
    } catch (exception) {
      setOptionErrors((current) => ({ ...current, [id]: exception instanceof Error ? exception.message : "Could not load set options" }));
    }
  };

  const search = async (
    selected = state.selected,
    mode = state.mode,
    conditions = state.conditions,
  ) => {
    if (!selected.length) return;
    setSearching(true);
    setError(null);
    try {
      const queryConditions = mode === "advanced" ? selected.flatMap((id) => {
        const condition = conditions[id] ?? emptyCondition();
        return condition.moves.length || condition.item || condition.ability || condition.nature ? [{ pokemon_id: id, ...condition }] : [];
      }) : [];
      const response = await api.searchTeams({
        mode,
        team: { contains: selected, conditions: queryConditions },
        tournaments: { min_players: settings.minPlayers },
      });
      setResult(response);
      setReferenceKey(null);
      setExpanded(new Set(mode === "advanced" && response.results.length ? [0] : []));
    } catch (exception) {
      setError(exception instanceof Error ? exception.message : "Could not search teams");
    } finally {
      setSearching(false);
    }
  };

  const openVariants = (item: TeamSearchResult) => {
    const selected = item.pokemon.map((pokemon) => pokemon.id);
    const conditions = state.mode === "basic" ? {} : state.conditions;
    setState((current) => ({ ...current, mode: "advanced", selected, conditions }));
    void search(selected, "advanced", conditions);
    document.getElementById("team-search")?.scrollIntoView({ behavior: "smooth" });
  };

  const byId = new Map(species.map((pokemon) => [pokemon.id, pokemon]));
  const labels = (id: string) => {
    const condition = state.conditions[id];
    return condition ? [...condition.moves, condition.item, condition.ability, condition.nature].filter(Boolean) as string[] : [];
  };
  const exact = state.selected.length === 6;
  const help = state.mode === "basic"
    ? exact ? "With six Pokémon, we will search for this exact composition." : "We will show complete six-Pokémon compositions containing your selection."
    : "We will show exact team lists; you can specify any selected Pokémon's set.";
  const status = catalogError ?? (loading ? "Loading dataset…" : health ? `${formatNumber(health.tournaments)} tournaments · ${formatNumber(health.teams)} teams` : "Dataset unavailable");

  return (
    <>
      <AppHeader
        active="teams"
        status={status}
        settings={settings}
        onSettingsChange={(nextSettings) => {
          if (nextSettings.minPlayers !== settings.minPlayers) { setOptions({}); setResult(null); }
          setSettings(nextSettings);
        }}
      />
      <main>
        <div className="team-view-header"><div><h1>Find teams</h1><p>Find six-Pokémon compositions or exact team lists with their complete sets.</p></div><span>Regulation M-B · public team lists</span></div>
        {error && <p id="team-error" role="alert">{error}</p>}
        <section id="team-search" className="team-search-panel" aria-labelledby="team-query-title">
          <div className="search-mode-switch" aria-label="Search type">
            <button type="button" aria-pressed={state.mode === "basic"} onClick={() => setMode("basic")}><b>1</b><span><strong>Basic search</strong><em>Six-Pokémon compositions from a selection of 1–6.</em></span></button>
            <button type="button" aria-pressed={state.mode === "advanced"} onClick={() => setMode("advanced")}><b>2</b><span><strong>Advanced search</strong><em>Real team lists with moves, items, abilities, and natures.</em></span></button>
          </div>
          <div className="team-query-body">
            <div className="team-query-header"><h2 id="team-query-title">Pokémon the team must include</h2><span>{state.selected.length}/6</span></div>
            <div className="team-selection">
              {state.selected.map((id) => {
                const pokemon = byId.get(id);
                const selectedLabels = labels(id);
                return (
                  <article
                    key={id}
                    className={`team-selected-pokemon${selectedLabels.length ? " conditioned" : ""}`}
                    data-edit-condition={state.mode === "advanced" ? "" : undefined}
                    role={state.mode === "advanced" ? "button" : undefined}
                    tabIndex={state.mode === "advanced" ? 0 : undefined}
                    aria-label={state.mode === "advanced" ? `Edit ${pokemon?.name ?? id}'s set` : undefined}
                    onClick={(event) => { if (state.mode === "advanced" && !(event.target as HTMLElement).closest(".team-remove")) void openConditions(id); }}
                    onKeyDown={(event) => { if (state.mode === "advanced" && (event.key === "Enter" || event.key === " ")) { event.preventDefault(); void openConditions(id); } }}
                  >
                    <PokemonSprite id={id} imageIds={imageIds} />
                    <div><strong>{pokemon?.name ?? id}</strong>{state.mode === "advanced" && <span className="team-set-trigger">{selectedLabels.length ? selectedLabels.join(" · ") : "+ Specify set"}</span>}</div>
                    <button className="team-remove" type="button" aria-label={`Remove ${pokemon?.name ?? id}`} onClick={() => {
                      const conditions = { ...state.conditions }; delete conditions[id];
                      setState((current) => ({ ...current, selected: current.selected.filter((value) => value !== id), conditions }));
                      setResult(null);
                    }}>×</button>
                  </article>
                );
              })}
              {!exact && <button className="team-add-pokemon" type="button" onClick={() => setPickerOpen(true)}>+ Add Pokémon</button>}
            </div>
            <div className="team-query-actions">
              <p>{help}</p>
              <button className="secondary-action" type="button" onClick={() => { setState((current) => ({ ...current, selected: [], conditions: {} })); setResult(null); }}>Clear</button>
              <button className="primary-action" type="button" disabled={!state.selected.length || searching} onClick={() => void search()}>{searching ? "Searching…" : state.mode === "basic" ? "Find compositions" : "Find teams"}</button>
            </div>
          </div>
        </section>
        <TeamResults
          mode={state.mode}
          selectedCount={state.selected.length}
          result={result}
          imageIds={imageIds}
          conditions={state.conditions}
          expanded={expanded}
          referenceKey={referenceKey}
          detailMode={detailMode}
          showTies={settings.showTies}
          onDetailModeChange={setDetailMode}
          onToggle={(index) => setExpanded((current) => { const next = new Set(current); next.has(index) ? next.delete(index) : next.add(index); return next; })}
          onReference={(index) => { if (result) { setReferenceKey(result.results[index].key); setExpanded((current) => new Set(current).add(index)); } }}
          onOpenVariants={openVariants}
        />
      </main>
      <PokemonPicker
        open={pickerOpen}
        species={species}
        imageIds={imageIds}
        blocked={state.selected}
        defaultKeepOpen
        onPick={(id) => {
          const selected = [...new Set([...state.selected, id])].slice(0, 6);
          setState((current) => ({ ...current, selected }));
          setResult(null);
          return selected.length === 6;
        }}
        onClose={() => setPickerOpen(false)}
      />
      <ConditionDialog
        pokemonId={editing}
        species={species}
        options={editing ? options[editing] : undefined}
        value={editing ? state.conditions[editing] ?? emptyCondition() : emptyCondition()}
        error={editing ? optionErrors[editing] : null}
        onApply={(condition) => { if (editing) setState((current) => ({ ...current, conditions: { ...current.conditions, [editing]: condition } })); setEditing(null); setResult(null); }}
        onClear={() => { if (editing) { const conditions = { ...state.conditions }; delete conditions[editing]; setState((current) => ({ ...current, conditions })); } setEditing(null); setResult(null); }}
        onClose={() => setEditing(null)}
      />
    </>
  );
}
