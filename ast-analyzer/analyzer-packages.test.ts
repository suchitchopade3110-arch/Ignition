/**
 * P2 "Shallow package diffing": only the root package.json was diffed, by
 * declared range. Now package-lock.json v3's `packages` map is diffed too
 * (resolved versions, transitive changes), and every changed
 * **\/package.json and **\/package-lock.json in a monorepo is read at base
 * and head.
 */
import { afterAll, beforeAll, describe, expect, test } from "bun:test";
import { mkdirSync, mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";
import * as analyzer from "./analyzer";

// Looked up at call time, so a missing export fails its own tests only.
const lockfilePackages = (text: string) => (analyzer as any).lockfilePackages(text) as Map<string, Set<string>>;
const diffLockfiles = (b: unknown, h: unknown) => (analyzer as any).diffLockfiles(b, h) as any[];
const changedPackages = (g: string, b: string, h: string) => (analyzer as any).changedPackages(g, b, h) as Promise<any[]>;

const lock = (packages: Record<string, unknown>) =>
  JSON.stringify({ name: "mono", lockfileVersion: 3, requires: true, packages });

const BASE_LOCK = lock({
  "": { name: "mono", workspaces: ["packages/*"] },
  "packages/web": { name: "web", version: "1.0.0" },
  "node_modules/web": { resolved: "packages/web", link: true },
  "node_modules/react": { version: "18.3.1" },
  "node_modules/loose-envify": { version: "1.4.0" },
  "node_modules/old/node_modules/minimist": { version: "1.2.5" },
});

const HEAD_LOCK = lock({
  "": { name: "mono", workspaces: ["packages/*"] },
  "packages/web": { name: "web", version: "1.0.0" },
  "node_modules/web": { resolved: "packages/web", link: true },
  "node_modules/react": { version: "18.3.1" },
  "node_modules/loose-envify": { version: "1.4.1" },              // transitive bump
  "node_modules/old/node_modules/minimist": { version: "1.2.5" },
  "node_modules/left-pad": { version: "1.3.0" },                  // new transitive
  "node_modules/@scope/pkg": { version: "2.0.0" },               // new scoped
});

describe("lockfilePackages", () => {
  test("reads resolved versions from the v3 packages map, nested and scoped, skipping the root and links", () => {
    const pkgs = lockfilePackages(HEAD_LOCK);
    expect([...pkgs.entries()].map(([n, v]) => [n, [...v]]).sort()).toEqual([
      ["@scope/pkg", ["2.0.0"]],
      ["left-pad", ["1.3.0"]],
      ["loose-envify", ["1.4.1"]],
      ["minimist", ["1.2.5"]],
      ["react", ["18.3.1"]],
    ]);
  });

  test("a lockfile without a packages map (v1) or invalid JSON yields nothing", () => {
    expect(lockfilePackages(JSON.stringify({ lockfileVersion: 1, dependencies: {} })).size).toBe(0);
    expect(lockfilePackages("{not json").size).toBe(0);
  });
});

describe("diffLockfiles", () => {
  test("reports transitive bumps with the previous version and new packages without one", () => {
    const changed = diffLockfiles(lockfilePackages(BASE_LOCK), lockfilePackages(HEAD_LOCK));
    expect(changed.sort((a, b) => a.name.localeCompare(b.name))).toEqual([
      { name: "@scope/pkg", version: "2.0.0" },
      { name: "left-pad", version: "1.3.0" },
      { name: "loose-envify", version: "1.4.1", previous_version: "1.4.0" },
    ]);
  });

  test("a new lockfile (no base) reports every package as new", () => {
    expect(diffLockfiles(null, lockfilePackages(BASE_LOCK)).map((p) => p.name).sort()).toEqual(
      ["loose-envify", "minimist", "react"],
    );
  });
});

describe("changedPackages on a real monorepo", () => {
  let root: string;
  let gitDir: string;
  let base: string;
  let head: string;

  const sh = (args: string[]) => {
    const p = Bun.spawnSync(["git", ...args], { cwd: root, stdout: "pipe", stderr: "pipe" });
    if (p.exitCode !== 0) throw new Error(p.stderr.toString());
    return p.stdout.toString().trim();
  };
  const write = (rel: string, body: string) => {
    mkdirSync(path.dirname(path.join(root, rel)), { recursive: true });
    writeFileSync(path.join(root, rel), body);
  };

  beforeAll(() => {
    root = mkdtempSync(path.join(tmpdir(), "ign-pkgs-"));
    sh(["init", "-q", "-b", "main"]);
    sh(["config", "user.email", "t@t"]);
    sh(["config", "user.name", "t"]);
    write("package.json", JSON.stringify({ name: "mono", workspaces: ["packages/*"] }));
    write("packages/web/package.json", JSON.stringify({ name: "web", dependencies: { react: "^18.3.1" } }));
    write("packages/api/package.json", JSON.stringify({ name: "api", dependencies: { express: "^4.19.0" } }));
    write("package-lock.json", BASE_LOCK);
    sh(["add", "-A"]); sh(["commit", "-qm", "base"]);
    base = sh(["rev-parse", "HEAD"]);
    // The PR: a new dependency in one workspace, a lockfile with a transitive
    // bump, and a node_modules package.json that must be ignored.
    write("packages/web/package.json",
      JSON.stringify({ name: "web", dependencies: { react: "^18.3.1", "left-pad": "^1.3.0" } }));
    write("package-lock.json", HEAD_LOCK);
    // A new workspace whose dependency no lockfile covers (e.g. not yet
    // installed): only its own package.json can report it.
    write("packages/cli/package.json", JSON.stringify({ name: "cli", dependencies: { commander: "^12.1.0" } }));
    write("vendor/node_modules/evil/package.json", JSON.stringify({ name: "evil", dependencies: { x: "1.0.0" } }));
    sh(["add", "-A", "-f"]); sh(["commit", "-qm", "head"]);
    head = sh(["rev-parse", "HEAD"]);
    gitDir = path.join(root, ".git");
  });

  afterAll(() => rmSync(root, { recursive: true, force: true }));

  test("every changed manifest and lockfile is diffed; resolved lockfile versions win", async () => {
    const changed = await changedPackages(gitDir, base, head);
    expect(changed.sort((a, b) => a.name.localeCompare(b.name))).toEqual([
      { name: "@scope/pkg", version: "2.0.0" },
      { name: "commander", version: "12.1.0" },
      { name: "left-pad", version: "1.3.0" },
      { name: "loose-envify", version: "1.4.1", previous_version: "1.4.0" },
    ]);
  });

  test("an unchanged workspace manifest is not reported", async () => {
    const names = (await changedPackages(gitDir, base, head)).map((p) => p.name);
    expect(names).not.toContain("express");
    expect(names).not.toContain("x");
  });
});
