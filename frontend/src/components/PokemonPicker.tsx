import { useEffect, useMemo, useState } from "react";

import { formatNumber } from "../format";
import type { Species } from "../types";
import { Modal } from "./Modal";
import { PokemonSprite } from "./PokemonSprite";

interface Props {
  open: boolean;
  species: Species[];
  imageIds: Record<string, number>;
  blocked: string[];
  defaultKeepOpen: boolean;
  onPick: (id: string) => boolean;
  onClose: () => void;
}

export function PokemonPicker({ open, species, imageIds, blocked, defaultKeepOpen, onPick, onClose }: Props) {
  const [query, setQuery] = useState("");
  const [keepOpen, setKeepOpen] = useState(defaultKeepOpen);
  const matches = useMemo(() => {
    const normalized = query.trim().toLocaleLowerCase("en");
    const blockedIds = new Set(blocked);
    return species.filter((pokemon) =>
      !blockedIds.has(pokemon.id) && pokemon.name.toLocaleLowerCase("en").includes(normalized),
    );
  }, [blocked, query, species]);

  useEffect(() => {
    if (open) {
      setQuery("");
      setKeepOpen(defaultKeepOpen);
    }
  }, [defaultKeepOpen, open]);

  return (
    <Modal id="pokemon-picker" open={open} onClose={onClose}>
      <div className="picker-header">
        <div><h2>Add Pokémon</h2><p>Search and add one or more Pokémon.</p></div>
        <button type="button" aria-label="Close picker" onClick={onClose}>×</button>
      </div>
      <div className="picker-toolbar">
        <input autoFocus type="search" placeholder="Search Pokémon…" autoComplete="off" value={query} onChange={(event) => setQuery(event.target.value)} />
        <label><input type="checkbox" checked={keepOpen} onChange={(event) => setKeepOpen(event.target.checked)} />Add multiple</label>
      </div>
      <div className="pokemon-grid">
        {matches.map((pokemon) => (
          <button
            key={pokemon.id}
            className="pokemon-choice"
            type="button"
            onClick={() => { if (onPick(pokemon.id) || !keepOpen) onClose(); }}
          >
            <PokemonSprite id={pokemon.id} imageIds={imageIds} />
            <span><strong>{pokemon.name}</strong><span>{formatNumber(pokemon.teams)} teams</span></span>
          </button>
        ))}
        {!matches.length && <p className="picker-empty">No matching Pokémon.</p>}
      </div>
    </Modal>
  );
}
