import type {
  FieldDifference,
  ScalarField,
  TeamDifference,
  TeamSearchResult,
} from "../../types";

const scalarFields: ScalarField[] = ["item", "ability", "nature"];
const normalized = (value: unknown) => String(value ?? "").trim().toLocaleLowerCase("en");

export function compareVariants(
  reference: TeamSearchResult | undefined,
  candidate: TeamSearchResult,
): TeamDifference {
  if (!reference || reference.key === candidate.key) return { pokemon: [], changes: 0 };

  const referencePokemon = new Map(reference.pokemon.map((pokemon) => [pokemon.id, pokemon]));
  const pokemon = candidate.pokemon.flatMap((current) => {
    const previous = referencePokemon.get(current.id);
    if (!previous) return [];

    const fields: FieldDifference[] = scalarFields.flatMap((field) =>
      normalized(previous[field]) === normalized(current[field])
        ? []
        : [{ field, before: previous[field] || "—", after: current[field] || "—" }],
    );
    const previousMoves = new Map(previous.moves.map((move) => [normalized(move), move.trim()]));
    const currentMoves = new Map(current.moves.map((move) => [normalized(move), move.trim()]));
    const removed = [...previousMoves]
      .filter(([key]) => !currentMoves.has(key))
      .map(([, move]) => move);
    const added = [...currentMoves]
      .filter(([key]) => !previousMoves.has(key))
      .map(([, move]) => move);

    if (removed.length || added.length) fields.push({ field: "moves", removed, added });
    return fields.length ? [{ id: current.id, name: current.name, fields }] : [];
  });

  return {
    pokemon,
    changes: pokemon.reduce(
      (total, member) => total + member.fields.reduce(
        (count, field) => count + (field.field === "moves" ? Math.max(field.removed.length, field.added.length) : 1),
        0,
      ),
      0,
    ),
  };
}
