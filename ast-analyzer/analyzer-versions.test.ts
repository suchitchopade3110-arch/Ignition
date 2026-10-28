/**
 * Declared dependency ranges must become a concrete version OSV/npm can
 * look up — or be skipped when there isn't one — before Agent 2C sees them
 * (P2 "shallow package diffing", the part the P0 patch covers).
 */
import { describe, expect, test } from "bun:test";

import { diffPackages, normalizeVersion } from "./analyzer";

describe("normalizeVersion", () => {
  test("turns common range syntaxes into a concrete version", () => {
    expect(normalizeVersion(">=1.2.0")?.version).toBe("1.2.0");
    expect(normalizeVersion("1.x")?.version).toBe("1.0.0");
    expect(normalizeVersion("~2.3.4")?.version).toBe("2.3.4");
    expect(normalizeVersion("^1.2.3-beta.1")?.version).toBe("1.2.3-beta.1");
  });

  test("resolves npm: aliases to the real package name", () => {
    expect(normalizeVersion("npm:lodash@^4.17.21")).toEqual({ version: "4.17.21", alias: "lodash" });
  });

  test("skips specs that have no registry version", () => {
    for (const spec of ["workspace:*", "file:../x", "link:../y", "git+https://github.com/a/b.git", "github:a/b", "https://x.test/a.tgz", "latest"]) {
      expect(normalizeVersion(spec)).toBeNull();
    }
  });
});

describe("diffPackages with normalized versions", () => {
  test("reports an aliased dependency under its real name and drops non-registry specs", () => {
    const changed = diffPackages({}, { "my-lodash": "npm:lodash@^4.17.21", local: "workspace:*", react: ">=19.0.0" });
    expect(changed).toEqual([
      { name: "lodash", version: "4.17.21" },
      { name: "react", version: "19.0.0" },
    ]);
  });
});
