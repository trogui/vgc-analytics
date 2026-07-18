import type { CSSProperties } from "react";

import { itemIconUrl, moveType, TYPE_COLORS } from "../pokemonData";

export function MovePill({ move, className = "" }: { move: string; className?: string }) {
  const type = moveType(move);
  const style = type ? { "--move-color": TYPE_COLORS[type] } as CSSProperties : undefined;
  return (
    <span className={`move-pill${type ? " has-type" : ""}${className ? ` ${className}` : ""}`} style={style}>
      {type && <img className="move-type-icon" src={`/static/type-icons/${type.toLowerCase()}.png`} alt="" title={type} />}
      {move}
    </span>
  );
}

export function ItemName({ item }: { item: string }) {
  const icon = itemIconUrl(item);
  return <>{icon && <img className="item-icon" src={icon} alt="" />}{item}</>;
}
