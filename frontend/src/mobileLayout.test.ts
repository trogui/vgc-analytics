import { expect, test } from "vitest";
import { readFileSync } from "node:fs";

const styles = readFileSync(new URL("./styles.css", import.meta.url), "utf8");

function rule(selector: string) {
  const match = styles.match(new RegExp(`${selector.replace(".", "\\.")}\\s*\\{([^}]*)\\}`));
  expect(match, `missing ${selector} rule`).not.toBeNull();
  return match?.[1] ?? "";
}

test("selected content cannot make its panel, roster, or team container grow wider", () => {
  for (const selector of [".pokemon-roster", ".team-selection"]) {
    const declarations = rule(selector);
    expect(declarations).toMatch(/width:\s*100%/);
    expect(declarations).toMatch(/min-width:\s*0/);
  }
  expect(rule(".analysis-grid > .panel")).toMatch(/width:\s*100%/);
});
