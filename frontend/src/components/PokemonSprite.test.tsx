import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { PokemonSprite } from "./PokemonSprite";

describe("PokemonSprite", () => {
  it("does not request artwork before it enters the viewport", () => {
    const html = renderToStaticMarkup(<PokemonSprite id="pikachu" imageIds={{ pikachu: 25 }} />);

    expect(html).toContain("<img");
    expect(html).not.toContain("src=");
  });
});
