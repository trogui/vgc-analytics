import { expect, test } from "vitest";

import { formatRecord } from "./format";

const record = { wins: 13069, losses: 12451, ties: 42 };

test("formats records with optional ties", () => {
  expect(formatRecord(record, true)).toBe("13,069 - 12,451 - 42");
  expect(formatRecord(record, false)).toBe("13,069 - 12,451");
});
