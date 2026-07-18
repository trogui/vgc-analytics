import { useCallback, useEffect, useState } from "react";

import { api } from "../api";
import type { Health, Species } from "../types";

export function useCatalog(minPlayers: number) {
  const [species, setSpecies] = useState<Species[]>([]);
  const [imageIds, setImageIds] = useState<Record<string, number>>({});
  const [health, setHealth] = useState<Health | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const loadAll = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [nextHealth, nextSpecies, nextImages] = await Promise.all([
        api.health(),
        api.species(minPlayers),
        api.pokemonImages(),
      ]);
      setHealth(nextHealth);
      setSpecies(nextSpecies);
      setImageIds(nextImages);
    } catch (exception) {
      setError(exception instanceof Error ? exception.message : "Could not load the dataset");
    } finally {
      setLoading(false);
    }
  }, [minPlayers]);

  useEffect(() => { void loadAll(); }, [loadAll]);

  return { species, imageIds, health, error, loading, reload: loadAll };
}
