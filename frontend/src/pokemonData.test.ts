import { describe, expect, it } from "vitest";

import { itemIconUrl, moveType } from "./pokemonData";

describe("Pokémon metadata", () => {
  it("maps formatting variants and known source typos", () => {
    expect(moveType("Will-O-Wisp")).toBe("Fire");
    expect(moveType("dazziling gleam")).toBe("Fairy");
    expect(moveType("not a move")).toBeNull();
    expect(itemIconUrl("Focus Sash")).toContain("focus-sash.png");
    expect(itemIconUrl("Scraftinite")).toBeNull();
  });
});
