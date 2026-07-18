import { PokemonSprite } from "../../components/PokemonSprite";
import type { FieldDifference, PokemonCondition, PokemonDifference, TeamPokemon } from "../../types";

interface Props {
  pokemon: TeamPokemon;
  requested: PokemonCondition;
  imageIds: Record<string, number>;
  difference?: PokemonDifference;
  unchanged?: boolean;
}

export function TeamSetCard({ pokemon, requested, imageIds, difference, unchanged = false }: Props) {
  const changes = new Map(difference?.fields.map((change) => [change.field, change]) ?? []);
  const value = (label: string, field: "item" | "ability" | "nature") => {
    const change = changes.get(field) as Extract<FieldDifference, { field: typeof field }> | undefined;
    return change
      ? <div className="team-set-value changed"><dt>{label}</dt><dd><del>{change.before}</del><ins>{change.after}</ins></dd></div>
      : <div className="team-set-value"><dt>{label}</dt><dd>{pokemon[field] || "—"}</dd></div>;
  };
  const moveChange = changes.get("moves") as Extract<FieldDifference, { field: "moves" }> | undefined;
  const changedMoves = new Set([...(moveChange?.removed ?? []), ...(moveChange?.added ?? [])].map((move) => move.trim().toLocaleLowerCase("en")));
  const moveRows = pokemon.moves
    .filter((move) => !changedMoves.has(move.trim().toLocaleLowerCase("en")))
    .map((move) => <span key={move} className={requested.moves.includes(move) ? "match" : ""}>{move}</span>);
  if (moveChange) {
    for (let index = 0; index < Math.max(moveChange.removed.length, moveChange.added.length); index += 1) {
      moveRows.push(<span key={`change-${index}`} className="changed"><del>{moveChange.removed[index] || "—"}</del><ins>{moveChange.added[index] || "—"}</ins></span>);
    }
  }

  return (
    <section className={`team-set-card${difference ? " has-differences" : ""}${unchanged ? " is-unchanged" : ""}`}>
      <div className="team-set-head"><PokemonSprite id={pokemon.id} imageIds={imageIds} /><strong>{pokemon.name}</strong></div>
      <dl>{value("Item", "item")}{value("Ability", "ability")}{value("Nature", "nature")}</dl>
      <div className="team-moves">{moveRows.length ? moveRows : <span>No published moves</span>}</div>
    </section>
  );
}
