import { ConditionFilters } from "../../components/ConditionFilters";
import { PokemonSprite } from "../../components/PokemonSprite";
import { formatNumber } from "../../format";
import type { PokemonCondition, PokemonOptions, Side, Species } from "../../types";

interface Props {
  side: Side;
  pokemonId: string | null;
  species: Species[];
  imageIds: Record<string, number>;
  options?: PokemonOptions;
  condition: PokemonCondition;
  error?: string | null;
  onChange: (value: PokemonCondition) => void;
  onClose: () => void;
}

export function ConditionDrawer({ side, pokemonId, species, imageIds, options, condition, error, onChange, onClose }: Props) {
  const opponent = side === "opponent";
  const pokemon = species.find((item) => item.id === pokemonId);
  return (
    <aside
      id={`condition-drawer-${side}`}
      className={`condition-drawer ${opponent ? "right" : "left"}`}
      aria-labelledby={`drawer-title-${side}`}
      aria-hidden={!pokemonId}
    >
      <div className="drawer-header">
        <div><h2 id={`drawer-title-${side}`}>{opponent ? "Opponent conditions" : "Your conditions"}</h2><p>Only options observed in public team lists.</p></div>
        <button type="button" aria-label={`Close ${opponent ? "opponent" : "your"} conditions`} onClick={onClose}>×</button>
      </div>
      {pokemonId && (
        <>
          <div className="drawer-pokemon">
            <PokemonSprite id={pokemonId} name="" imageIds={imageIds} large />
            <div><strong>{pokemon?.name ?? pokemonId}</strong><span>{options ? formatNumber(options.teams) : "—"} observed teams · {opponent ? "Opponent" : "My selection"}</span></div>
          </div>
          <div className="drawer-content">
            {error && <p className="drawer-loading">{error}</p>}
            {!error && !options && <p className="drawer-loading">Loading observed conditions…</p>}
            {options && <ConditionFilters options={options} value={condition} onChange={onChange} expandable />}
          </div>
        </>
      )}
    </aside>
  );
}
