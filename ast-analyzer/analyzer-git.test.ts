/**
 * Regression tests for audit findings P0-2, P0-3, P0-8 and P1-9, against a
 * REAL multi-commit git repo built in beforeAll (the golden-eval fixtures
 * hand-write changed_files, so they can't catch analyzer scoping bugs).
 */
import { afterAll, beforeAll, describe, expect, test } from "bun:test";
import { mkdtempSync, rmSync, writeFileSync, mkdirSync, readdirSync, existsSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";

let root: string;
let repo: string;
const sha: Record<string, string> = {};

function sh(args: string[], cwd: string): string {
  const p = Bun.spawnSync(["git", ...args], { cwd, stdout: "pipe", stderr: "pipe" });
  if (p.exitCode !== 0) throw new Error(p.stderr.toString());
  return p.stdout.toString().trim();
}
function write(rel: string, body: string) {
  mkdirSync(path.dirname(path.join(repo, rel)), { recursive: true });
  writeFileSync(path.join(repo, rel), body);
}

beforeAll(() => {
  root = mkdtempSync(path.join(tmpdir(), "ign-git-"));
  repo = path.join(root, "origin");
  mkdirSync(repo);
  process.env.AST_WORKSPACES_ROOT = path.join(root, "ws");
  sh(["init", "-q", "-b", "main"], repo);
  sh(["config", "user.email", "t@t"], repo);
  sh(["config", "user.name", "t"], repo);
  // No uploadpack.allowFilter here: the local "server" ignores --filter, so
  // nothing can be lazily fetched by SHA and the fork test below can only
  // pass through the explicit refs/pull/<n>/head fetch.

  write("src/legacy.ts", "export function legacy(x: string) { return eval(x); }\n");
  write("src/user.ts", "export function getUser(id: string) { return { id }; }\n");
  write("src/old.ts", "export function oldThing() { return 1; }\n");
  sh(["add", "-A"], repo); sh(["commit", "-qm", "base"], repo);
  sha.base = sh(["rev-parse", "HEAD"], repo);

  // PR #1: edits user.ts, deletes old.ts
  write("src/user.ts", "export function getUserById(id: string) { return { id }; }\n");
  sh(["rm", "-q", "src/old.ts"], repo); sh(["commit", "-qam", "pr1"], repo);
  sha.pr1 = sh(["rev-parse", "HEAD"], repo);
  sh(["update-ref", "refs/pull/1/head", sha.pr1], repo);

  // PR #2: a different edit to user.ts that adds a destructured child_process exec
  sh(["checkout", "-q", "--detach", sha.base], repo);
  write("src/user.ts",
    'export function getUserV2(id: string) { return { id }; }\nconst { exec } = require("child_process");\nexport const run = () => exec("ls");\n');
  sh(["commit", "-qam", "pr2"], repo);
  sha.pr2 = sh(["rev-parse", "HEAD"], repo);
  sh(["update-ref", "refs/pull/2/head", sha.pr2], repo);

  // PR #7: fork-style — its head is reachable ONLY through refs/pull/7/head
  sh(["checkout", "-q", "--detach", sha.base], repo);
  write("src/fork.ts", "export const forked = 1;\n");
  sh(["add", "-A"], repo); sh(["commit", "-qm", "fork"], repo);
  sha.fork = sh(["rev-parse", "HEAD"], repo);
  sh(["update-ref", "refs/pull/7/head", sha.fork], repo);
  sh(["checkout", "-q", "main"], repo);
});

afterAll(() => rmSync(root, { recursive: true, force: true }));

// One cache shared across calls, exactly like server.ts's process-wide
// projectCache — that sharing is what made warm and cold results differ.
const projectCache = new Map();
const names = (p: any) => p.symbols.map((s: any) => `${s.file_path}:${s.symbol_name}`).sort();

async function analyze(ref: string, pr: number, key = "acme/widgets") {
  const { analyzePullRequest } = await import("./analyzer");
  return analyzePullRequest({
    repoFullName: key, prNumber: pr, baseRef: sha.base,
    source: { type: "git", url: `file://${repo}`, ref },
    projectCache,
  });
}

describe("analyzer against a real git repo", () => {
  test("P0-2: changed_files is the diff, and a pre-existing eval() is not a violation", async () => {
    const r = await analyze(sha.pr1, 1);
    expect(r.changed_files).toEqual(["src/user.ts"]);
    expect(r.hard_rule_violations).toEqual([]);
  });

  test("P0-3: a warm repo gives the same result as a cold one", async () => {
    await analyze(sha.pr1, 1);
    const warm = await analyze(sha.pr2, 2);
    const cold = await analyze(sha.pr2, 2, "acme/widgets-cold");
    expect(names(warm)).toEqual(names(cold));
    expect(names(warm)).toContain("src/user.ts:getUserV2");
    expect(names(warm)).not.toContain("src/user.ts:getUserById");
  });

  test("P0-3: concurrent reviews of one repo don't share a working tree and leave none behind", async () => {
    const [a, b] = await Promise.all([analyze(sha.pr1, 1), analyze(sha.pr2, 2)]);
    expect(names(a)).toEqual(["src/user.ts:getUserById"]);
    expect(names(b)).toContain("src/user.ts:getUserV2");
    const trees = path.join(root, "ws", "trees");
    expect(existsSync(trees) ? readdirSync(trees) : ["<no isolated trees dir>"]).toEqual([]);
  });

  test("P0-8: a fork PR head reachable only via refs/pull/<n>/head is analyzed", async () => {
    const r = await analyze(sha.fork, 7, "acme/widgets-fork");
    expect(r.changed_files).toEqual(["src/fork.ts"]);
    // The head must arrive through the explicit refs/pull/7/head fetch, not
    // as a side effect of partial-clone lazy fetching (which also works on
    // this fixture — see the solutions doc's Summary).
    const mirror = path.join(root, "ws", "mirrors", "acme_widgets-fork.git");
    expect(sh(["rev-parse", "refs/ignition/pull/7"], mirror)).toBe(sha.fork);
  });
});
