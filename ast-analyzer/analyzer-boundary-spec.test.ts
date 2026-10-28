/**
 * Audit P1-10: the boundary spec comes from the customer's repo, read at
 * the PR's BASE commit from the mirror, so a PR can't loosen its own rules.
 * Capped at 64 KB; no file means null.
 */
import { afterAll, beforeAll, describe, expect, test } from "bun:test";
import { mkdtempSync, rmSync, writeFileSync, mkdirSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";

let root: string;
const repos: Record<string, string> = {};
const sha: Record<string, string> = {};

const BASE_SPEC = [
  "version: 1",
  "layers:",
  "  - name: repositories",
  "    patterns: [\"src/repositories/**\"]",
  "  - name: routes",
  "    patterns: [\"src/routes/**\"]",
  "rules:",
  "  - from: repositories",
  "    to: routes",
  "    disallowed: true",
  "",
].join("\n");

function sh(args: string[], cwd: string): string {
  const p = Bun.spawnSync(["git", ...args], { cwd, stdout: "pipe", stderr: "pipe" });
  if (p.exitCode !== 0) throw new Error(p.stderr.toString());
  return p.stdout.toString().trim();
}

function initRepo(name: string): string {
  const dir = path.join(root, name);
  mkdirSync(dir);
  sh(["init", "-q", "-b", "main"], dir);
  sh(["config", "user.email", "t@t"], dir);
  sh(["config", "user.name", "t"], dir);
  return dir;
}

function write(repo: string, rel: string, body: string) {
  mkdirSync(path.dirname(path.join(repo, rel)), { recursive: true });
  writeFileSync(path.join(repo, rel), body);
}

beforeAll(() => {
  root = mkdtempSync(path.join(tmpdir(), "ign-spec-"));
  process.env.AST_WORKSPACES_ROOT = path.join(root, "ws");

  // Repo with a spec at base; PR #3 deletes the rule at its head.
  const withSpec = (repos.withSpec = initRepo("with-spec"));
  write(withSpec, "ignition.boundaries.yaml", BASE_SPEC);
  write(withSpec, "src/repositories/user.ts", "export const user = 1;\n");
  sh(["add", "-A"], withSpec); sh(["commit", "-qm", "base"], withSpec);
  sha.base = sh(["rev-parse", "HEAD"], withSpec);
  write(withSpec, "ignition.boundaries.yaml", "version: 1\nlayers: []\nrules: []\n");
  write(withSpec, "src/repositories/user.ts", "export const user = 2;\n");
  sh(["commit", "-qam", "loosen"], withSpec);
  sha.loosen = sh(["rev-parse", "HEAD"], withSpec);
  sh(["update-ref", "refs/pull/3/head", sha.loosen], withSpec);
  sh(["checkout", "-q", "--detach", sha.base], withSpec);

  // Repo with no spec at all.
  const noSpec = (repos.noSpec = initRepo("no-spec"));
  write(noSpec, "src/a.ts", "export const a = 1;\n");
  sh(["add", "-A"], noSpec); sh(["commit", "-qm", "base"], noSpec);
  sha.noSpecBase = sh(["rev-parse", "HEAD"], noSpec);
  write(noSpec, "src/a.ts", "export const a = 2;\n");
  sh(["commit", "-qam", "pr"], noSpec);
  sha.noSpecHead = sh(["rev-parse", "HEAD"], noSpec);
  sh(["update-ref", "refs/pull/1/head", sha.noSpecHead], noSpec);

  // Repo whose spec is over the 64 KB cap.
  const big = (repos.big = initRepo("big-spec"));
  write(big, "ignition.boundaries.yaml", BASE_SPEC + "#" + "x".repeat(70 * 1024) + "\n");
  write(big, "src/a.ts", "export const a = 1;\n");
  sh(["add", "-A"], big); sh(["commit", "-qm", "base"], big);
  sha.bigBase = sh(["rev-parse", "HEAD"], big);
  write(big, "src/a.ts", "export const a = 2;\n");
  sh(["commit", "-qam", "pr"], big);
  sha.bigHead = sh(["rev-parse", "HEAD"], big);
  sh(["update-ref", "refs/pull/1/head", sha.bigHead], big);
});

afterAll(() => rmSync(root, { recursive: true, force: true }));

async function analyze(repo: string, key: string, pr: number, base: string, head: string) {
  const { analyzePullRequest } = await import("./analyzer");
  return analyzePullRequest({
    repoFullName: key, prNumber: pr, baseRef: base,
    source: { type: "git", url: `file://${repo}`, ref: head },
    projectCache: new Map(),
  }) as Promise<any>;
}

describe("boundary spec from the customer's repo (P1-10)", () => {
  test("the spec is read at the base commit, so a PR can't loosen its own rules", async () => {
    const payload = await analyze(repos.withSpec, "acme/with-spec", 3, sha.base, sha.loosen);
    expect(payload.boundary_spec_yaml).toBe(BASE_SPEC);
    expect(payload.changed_files).toContain("src/repositories/user.ts");
  });

  test("no spec file means null", async () => {
    const payload = await analyze(repos.noSpec, "acme/no-spec", 1, sha.noSpecBase, sha.noSpecHead);
    expect(payload.boundary_spec_yaml).toBeNull();
  });

  test("a spec over 64 KB is not returned", async () => {
    const payload = await analyze(repos.big, "acme/big-spec", 1, sha.bigBase, sha.bigHead);
    expect(payload.boundary_spec_yaml).toBeNull();
  });
});
