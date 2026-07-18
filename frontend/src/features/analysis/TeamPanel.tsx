import type { PokemonCondition, Side, Species } from "../../types";
import { PokemonSprite } from "../../components/PokemonSprite";

interface Props {
  side: Side;
  species: Species[];
  imageIds: Record<string, number>;
  team: string[];
  disabled: string[];
  excludes: string[];
  conditions: Record<string, PokemonCondition>;
  openPokemon: string | null;
  onAdd: () => void;
  onRemove: (id: string) => void;
  onToggle: (id: string, enabled: boolean) => void;
  onEdit: (id: string) => void;
  onAddExclude: (id: string) => void;
  onRemoveExclude: (id: string) => void;
}

export function TeamPanel({
  side,
  species,
  imageIds,
  team,
  disabled,
  excludes,
  conditions,
  openPokemon,
  onAdd,
  onRemove,
  onToggle,
  onEdit,
  onAddExclude,
  onRemoveExclude,
}: Props) {
  const byId = new Map(species.map((pokemon) => [pokemon.id, pokemon]));
  const opponent = side === "opponent";
  const availableExcludes = species.filter((pokemon) => !team.includes(pokemon.id) && !excludes.includes(pokemon.id));

  return (
    <section id={opponent ? "opponent-panel" : undefined} className="panel selection-panel" aria-labelledby={`${side}-title`}>
      <div className="panel-header"><h2 id={`${side}-title`}>{opponent ? "Opponent Pokémon or core" : "Pokémon or core"}</h2><span>{team.length}/6</span></div>
      <div className="panel-body">
        <div className="pokemon-roster">
          {!team.length && (
            <div className="empty-roster">
              {opponent ? "No specific opponent: compare against the full sample." : "Add one or more Pokémon to analyze a core."}
            </div>
          )}
          {team.map((id) => {
            const pokemon = byId.get(id);
            const enabled = !disabled.includes(id);
            const values = conditions[id]
              ? [...conditions[id].moves, conditions[id].item, conditions[id].ability].filter(Boolean) as string[]
              : [];
            return (
              <article key={id} className={`pokemon-row${enabled ? "" : " is-disabled"}`}>
                <input
                  className="member-toggle"
                  type="checkbox"
                  checked={enabled}
                  aria-label={`Include ${pokemon?.name ?? id} in the analysis`}
                  onChange={(event) => onToggle(id, event.target.checked)}
                />
                <button
                  className="pokemon-open"
                  type="button"
                  aria-expanded={openPokemon === id}
                  aria-controls={`condition-drawer-${side}`}
                  aria-label={`Open or close conditions for ${pokemon?.name ?? id}`}
                  onClick={() => onEdit(id)}
                >
                  <PokemonSprite id={id} imageIds={imageIds} />
                  <span className="pokemon-copy">
                    <strong>{pokemon?.name ?? id}</strong>
                    <span className="condition-chips">
                      {values.length
                        ? values.map((value) => <span key={value} className="condition-chip">{value}</span>)
                        : <span className="condition-chip empty">No conditions</span>}
                    </span>
                  </span>
                </button>
                <button className="remove" type="button" aria-label={`Remove ${pokemon?.name ?? id}`} onClick={() => onRemove(id)}>Remove</button>
              </article>
            );
          })}
        </div>
        {team.length < 6 && <button className="add-pokemon" type="button" onClick={onAdd}>+ Add {opponent ? "opponent " : ""}Pokémon</button>}
        <details className="exclude-section">
          <summary>Exclude {opponent ? "opponent " : ""}Pokémon</summary>
          <div className="exclude-tokens">
            {excludes.map((id) => (
              <span key={id} className="exclude-token">
                {byId.get(id)?.name ?? id}
                <button type="button" aria-label={`Stop excluding ${byId.get(id)?.name ?? id}`} onClick={() => onRemoveExclude(id)}>×</button>
              </span>
            ))}
          </div>
          <select aria-label={`Exclude Pokémon from ${opponent ? "the opponent's" : "my"} team`} value="" onChange={(event) => onAddExclude(event.target.value)}>
            <option value="">Select Pokémon…</option>
            {availableExcludes.map((pokemon) => <option key={pokemon.id} value={pokemon.id}>{pokemon.name} ({pokemon.teams} teams)</option>)}
          </select>
        </details>
      </div>
    </section>
  );
}
