import { useEffect, useRef, useState } from "react";

const spriteVersion = "bf4c47ac82c33b330e33d98b8882d1cedb2f53e7";
const pending = new WeakMap<Element, () => void>();
let observer: IntersectionObserver | undefined;

function observe(image: HTMLImageElement, load: () => void) {
  observer ??= new IntersectionObserver((entries) => {
    for (const entry of entries) {
      if (!entry.isIntersecting) continue;
      pending.get(entry.target)?.();
      pending.delete(entry.target);
      observer?.unobserve(entry.target);
    }
  }, { rootMargin: "100px 0px" });
  pending.set(image, load);
  observer.observe(image);
  return () => {
    pending.delete(image);
    observer?.unobserve(image);
  };
}

interface Props {
  id: string;
  name?: string;
  imageIds: Record<string, number>;
}

export function PokemonSprite({ id, name = "", imageIds }: Props) {
  const imageId = imageIds[id];
  const image = useRef<HTMLImageElement>(null);
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    if (!image.current) return;
    if (!("IntersectionObserver" in window)) {
      setVisible(true);
      return;
    }
    return observe(image.current, () => setVisible(true));
  }, [imageId]);

  if (!imageId) return null;
  const src = `https://cdn.jsdelivr.net/gh/PokeAPI/sprites@${spriteVersion}/sprites/pokemon/other/official-artwork/${imageId}.png`;
  return <img ref={image} src={visible ? src : undefined} alt={name} decoding="async" />;
}
