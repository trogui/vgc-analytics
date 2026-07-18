import { useEffect, useState } from "react";

import { ConditionFilters } from "../../components/ConditionFilters";
import { Modal } from "../../components/Modal";
import type { PokemonCondition, PokemonOptions, Species } from "../../types";

interface Props {
  pokemonId: string | null;
  species: Species[];
  options?: PokemonOptions;
  value: PokemonCondition;
  error?: string | null;
  onApply: (value: PokemonCondition) => void;
  onClear: () => void;
  onClose: () => void;
}

export function ConditionDialog({ pokemonId, species, options, value, error, onApply, onClear, onClose }: Props) {
  const [draft, setDraft] = useState(value);
  useEffect(() => setDraft(value), [pokemonId, value]);
  const name = species.find((pokemon) => pokemon.id === pokemonId)?.name ?? pokemonId;
  return (
    <Modal id="team-condition-dialog" open={pokemonId !== null} onClose={onClose}>
      <div className="picker-header"><div><h2>Specify {name}'s set</h2><p>Only team lists matching every condition will appear.</p></div><button type="button" aria-label="Close conditions" onClick={onClose}>×</button></div>
      <div className="team-condition-content">
        {error && <p className="drawer-loading">{error}</p>}
        {!error && !options && <p className="drawer-loading">Loading options…</p>}
        {options && <ConditionFilters options={options} value={draft} onChange={setDraft} />}
      </div>
      <div className="team-condition-actions"><button className="secondary-action" type="button" onClick={onClear}>Remove conditions</button><button className="primary-action" type="button" disabled={!options} onClick={() => onApply(draft)}>Apply</button></div>
    </Modal>
  );
}
