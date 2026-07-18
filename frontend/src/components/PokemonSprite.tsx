const spriteVersion = "bf4c47ac82c33b330e33d98b8882d1cedb2f53e7";

interface Props {
  id: string;
  name?: string;
  imageIds: Record<string, number>;
  large?: boolean;
}

export function PokemonSprite({ id, name = "", imageIds, large = false }: Props) {
  const imageId = imageIds[id];
  if (!imageId) return null;
  const folder = large ? "other/official-artwork/" : "";
  const src = `https://cdn.jsdelivr.net/gh/PokeAPI/sprites@${spriteVersion}/sprites/pokemon/${folder}${imageId}.png`;
  return <img src={src} alt={name} />;
}
