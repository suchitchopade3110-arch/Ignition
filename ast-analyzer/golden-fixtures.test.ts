/**
 * The golden fixtures in tests/eval/real/ must be what the analyzer
 * produces today (P0-2 follow-up): regenerate them and compare.
 */
import { expect, test } from "bun:test";
import { readFileSync } from "node:fs";
import path from "node:path";
import { OUT_DIR, SPECS, generate } from "./scripts/golden-fixtures";

test("committed golden fixtures match fresh analyzer output", async () => {
  const fresh = await generate();
  for (const spec of SPECS) {
    const committed = JSON.parse(readFileSync(path.join(OUT_DIR, `${spec.name}.json`), "utf8"));
    expect(fresh[spec.name]).toEqual(committed);
  }
}, 60_000);
