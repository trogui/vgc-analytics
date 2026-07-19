import { Fragment } from "react";

import { PokemonSprite } from "../../components/PokemonSprite";
import { formatNumber, formatPercent, formatRecord, pluralize } from "../../format";
import type {
  DetailMode,
  PokemonCondition,
  SearchMode,
  TeamDifference,
  TeamSearchResponse,
  TeamSearchResult,
} from "../../types";
import { compareVariants } from "./compareVariants";
import { TeamSetCard } from "./TeamSetCard";

interface Props {
  mode: SearchMode;
  selectedCount: number;
  result: TeamSearchResponse | null;
  imageIds: Record<string, number>;
  conditions: Record<string, PokemonCondition>;
  expanded: Set<number>;
  referenceKey: string | null;
  detailMode: DetailMode;
  showTies: boolean;
  onDetailModeChange: (mode: DetailMode) => void;
  onToggle: (index: number) => void;
  onReference: (index: number) => void;
  onOpenVariants: (result: TeamSearchResult) => void;
}

function PokemonStrip({ result, imageIds, names = false }: { result: TeamSearchResult; imageIds: Record<string, number>; names?: boolean }) {
  return <div className="team-pokemon-strip">{result.pokemon.map((pokemon) => <span key={pokemon.id}><PokemonSprite id={pokemon.id} name={names ? pokemon.name : ""} imageIds={imageIds} />{names && <b>{pokemon.name}</b>}</span>)}</div>;
}

function ResultMetrics({ result, showTies }: { result: TeamSearchResult; showTies: boolean }) {
  return <div className="team-result-metrics">
    <div className="team-result-stat"><span>Win rate</span><strong>{formatPercent(result.win_rate)}</strong></div>
    <div className="team-result-stat"><span>Record</span><strong>{formatRecord(result.record, showTies)}</strong></div>
  </div>;
}

function changePreview(difference: TeamDifference) {
  const change = difference.pokemon[0];
  const field = change?.fields[0];
  if (!change || !field) return "";
  if (field.field !== "moves") return `${change.name}: ${field.before} → ${field.after}`;
  if (field.removed.length === 1 && field.added.length === 1) return `${change.name}: ${field.removed[0]} → ${field.added[0]}`;
  return `${change.name}: ${field.removed.length ? `−${field.removed.join(", ")}` : ""}${field.removed.length && field.added.length ? " · " : ""}${field.added.length ? `+${field.added.join(", ")}` : ""}`;
}

function Difference({ difference, reference, mostUsed }: { difference: TeamDifference; reference: boolean; mostUsed: boolean }) {
  if (reference) return <div className="team-variant-diff is-reference"><strong>Reference</strong><span>{mostUsed ? "Most used variant" : "Selected for comparison"}</span></div>;
  if (!difference.pokemon.length) return <div className="team-variant-diff"><strong>No visible differences</strong><span>Only the data formatting differs</span></div>;
  return <div className="team-variant-diff"><strong>{formatNumber(difference.pokemon.length)} Pokémon · {pluralize(difference.changes, "change")}</strong><span>{changePreview(difference)}</span></div>;
}

export function TeamResults({
  mode,
  selectedCount,
  result,
  imageIds,
  conditions,
  expanded,
  referenceKey,
  detailMode,
  showTies,
  onDetailModeChange,
  onToggle,
  onReference,
  onOpenVariants,
}: Props) {
  const exact = mode === "advanced" && selectedCount === 6;
  const reference = exact ? result?.results.find((item) => item.key === referenceKey) ?? result?.results[0] : undefined;
  const title = mode === "basic" ? "Compositions found" : "Teams found";
  const copy = result
    ? `${pluralize(result.total, "result")} · ${pluralize(result.matching_teams, "matching team list")}`
    : selectedCount ? "Press search to query public team lists." : "Select at least one Pokémon to get started.";

  return (
    <section className="team-results-section" aria-live="polite">
      <div className="team-results-header">
        <div><h2>{title}</h2><p>{copy}</p></div>
        {exact && result?.results.length ? (
          <span className="team-result-view" aria-label="Team detail view">
            <button type="button" aria-pressed={detailMode === "relative"} onClick={() => onDetailModeChange("relative")}>Relative to reference</button>
            <button type="button" aria-pressed={detailMode === "full"} onClick={() => onDetailModeChange("full")}>Full team</button>
          </span>
        ) : <span>Most used first</span>}
      </div>
      <div className="team-results">
        {!result && <div className="team-empty">{mode === "basic" ? "Basic search discovers complete cores; open any result to inspect its exact variants." : "Advanced search lets you require moves, an item, an ability, or a nature on selected Pokémon."}</div>}
        {result && !result.results.length && <div className="team-empty">No teams match all filters.</div>}
        {result?.results.map((item, index) => {
          if (mode === "basic") return (
            <article key={item.key} className="team-core-result">
              <div className="team-result-main"><span className="team-rank">{String(index + 1).padStart(2, "0")}</span><PokemonStrip result={item} imageIds={imageIds} names />
                <ResultMetrics result={item} showTies={showTies} />
                <button type="button" onClick={() => onOpenVariants(item)}>View {pluralize(item.variants, "variant")}</button>
              </div>
              <p>{pluralize(item.teams, "team list")} · {formatPercent(item.usage)} of matches · {pluralize(item.tournaments, "tournament")}</p>
            </article>
          );

          const opened = expanded.has(index);
          const isReference = exact && reference?.key === item.key;
          const difference = exact ? compareVariants(reference, item) : { pokemon: [], changes: 0 };
          const differenceByPokemon = new Map(difference.pokemon.map((pokemon) => [pokemon.id, pokemon]));
          const relative = exact && detailMode === "relative" && !isReference;
          const source = item.source ?? { placing: null, tournament: null };
          return (
            <article key={item.key} className={`team-sheet-result${isReference ? " is-reference" : ""}`}>
              <div
                className={`team-sheet-summary${exact ? " can-compare" : " can-open-variants"}`}
                role="button"
                tabIndex={0}
                aria-expanded={opened}
                aria-controls={`team-sheet-details-${index}`}
                aria-label={`${opened ? "Hide" : "Show"} ${relative ? "differences" : "sets"} for team ${index + 1}`}
                onClick={() => onToggle(index)}
                onKeyDown={(event) => {
                  if (event.key === "Enter" || event.key === " ") { event.preventDefault(); onToggle(index); }
                }}
              >
                <span className="team-rank">{String(index + 1).padStart(2, "0")}</span><PokemonStrip result={item} imageIds={imageIds} />
                {exact && <Difference difference={difference} reference={isReference} mostUsed={index === 0} />}
                <ResultMetrics result={item} showTies={showTies} />
                {exact && !isReference && <button className="team-use-reference" type="button" onClick={(event) => { event.stopPropagation(); onReference(index); }}>Use as reference</button>}
                {!exact && <button className="team-search-variants" type="button" onClick={(event) => { event.stopPropagation(); onOpenVariants(item); }}>Find variants</button>}
                <span className="team-disclosure" aria-hidden="true">{opened ? "▴" : "▾"}</span>
              </div>
              <p>{formatNumber(item.teams)}× observed · {source.tournament || "Unnamed tournament"}{source.placing ? ` · ${formatNumber(source.placing)}th` : ""}</p>
              <div id={`team-sheet-details-${index}`} className={`team-sheet-details${relative ? " is-comparison" : ""}`} hidden={!opened}>
                {item.pokemon.map((pokemon) => {
                  const pokemonDifference = differenceByPokemon.get(pokemon.id);
                  return <TeamSetCard
                    key={pokemon.id}
                    pokemon={pokemon}
                    requested={conditions[pokemon.id] ?? { moves: [], item: null, ability: null, nature: null }}
                    imageIds={imageIds}
                    difference={relative ? pokemonDifference : undefined}
                    unchanged={relative && !pokemonDifference}
                  />;
                })}
              </div>
            </article>
          );
        })}
      </div>
    </section>
  );
}
