import { describe, expect, it } from "vitest";

import { compareVariants } from "./compareVariants";
import type { TeamSearchResult } from "../../types";

const team = (key: string, item: string, moves = ["Protect"]): TeamSearchResult => ({
  key,
  teams: 1,
  tournaments: 1,
  variants: 1,
  usage: 1,
  pokemon: [{
    id: "basculegion",
    name: "Basculegion",
    item,
    ability: "Swift Swim",
    nature: "Adamant",
    moves,
  }],
  latest_date: "2026-07-18",
  record: { wins: 1, losses: 0, ties: 0 },
  win_rate: 1,
});

describe("compareVariants", () => {
  it("reports changed fields and move replacements", () => {
    const difference = compareVariants(
      team("reference", "Choice Band", ["Protect", "Wave Crash"]),
      team("candidate", "Basculegionite", ["Protect", "Aqua Jet"]),
    );

    expect(difference.changes).toBe(2);
    expect(difference.pokemon).toEqual([{
      id: "basculegion",
      name: "Basculegion",
      fields: [
        { field: "item", before: "Choice Band", after: "Basculegionite" },
        { field: "moves", removed: ["Wave Crash"], added: ["Aqua Jet"] },
      ],
    }]);
  });

  it("ignores casing and whitespace differences", () => {
    expect(compareVariants(
      team("reference", " Choice Band ", ["Protect"]),
      team("candidate", "choice band", [" protect "]),
    )).toEqual({ pokemon: [], changes: 0 });
  });
});
