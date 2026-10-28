/**
 * Regenerates golden-eval fixtures from REAL analyzer output (P0-2
 * follow-up). Each fixture below is built as a two-commit git repo (base,
 * then the PR's head), analyzePullRequest runs on it exactly as /analyze
 * does, and the real `git diff base head` plus the analyzer's payload are
 * written to tests/eval/real/<name>.json, which tests/eval/fixtures.py
 * loads. Nothing in those files is hand-written.
 *
 *   cd ast-analyzer && bun run scripts/golden-fixtures.ts          # write
 *   bun test golden-fixtures.test.ts                               # check for drift
 */
import { mkdirSync, mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";

export const GENERATED_BY = "ast-analyzer/scripts/golden-fixtures.ts";
export const OUT_DIR = path.resolve(import.meta.dir, "../../tests/eval/real");

type Files = Record<string, string>;
interface Spec { name: string; prNumber: number; base: Files; head: Files }

export const SPECS: Spec[] = [
  {
    name: "layer_crossing_repository_to_http_client",
    prNumber: 101,
    base: {
      "src/http/client.ts": "export const httpClient = {\n  get: async (url: string) => ({ url }),\n};\n",
      "src/repositories/user_repo.ts":
        "export class UserRepo {\n  async getUser(id: string) {\n    return { id };\n  }\n}\n",
    },
    head: {
      "src/repositories/user_repo.ts":
        "import { httpClient } from '../http/client';\nexport class UserRepo {\n  async getUser(id: string) {\n" +
        "    return httpClient.get(`/users/${id}`);\n  }\n}\n",
    },
  },
  {
    name: "hard_gate_rejects_eval_call_in_added_code",
    prNumber: 401,
    base: { "src/utils/dynamic_runner.ts": "export function runExpression(expr: string) {\n  return Number(expr);\n}\n" },
    head: { "src/utils/dynamic_runner.ts": "export function runExpression(expr: string) {\n  return eval(expr);\n}\n" },
  },
  {
    name: "off_by_one_in_pagination_slice",
    prNumber: 203,
    base: {
      "src/services/pagination_service.ts":
        "export function getPage<T>(items: T[], pageIndex: number, pageSize: number): T[] {\n" +
        "  return items.slice(pageIndex * pageSize, (pageIndex + 1) * pageSize);\n}\n",
    },
    head: {
      "src/services/pagination_service.ts":
        "export function getPage<T>(items: T[], pageIndex: number, pageSize: number): T[] {\n" +
        "  return items.slice(pageIndex * pageSize, pageIndex * pageSize + pageSize - 1);\n}\n",
    },
  },
];

function sh(args: string[], cwd: string): string {
  const p = Bun.spawnSync(["git", ...args], { cwd, stdout: "pipe", stderr: "pipe" });
  if (p.exitCode !== 0) throw new Error(p.stderr.toString());
  return p.stdout.toString();
}

function writeAll(repo: string, files: Files) {
  for (const [rel, body] of Object.entries(files)) {
    mkdirSync(path.dirname(path.join(repo, rel)), { recursive: true });
    writeFileSync(path.join(repo, rel), body);
  }
}

export async function generate(): Promise<Record<string, object>> {
  const root = mkdtempSync(path.join(tmpdir(), "ign-golden-"));
  const previousRoot = process.env.AST_WORKSPACES_ROOT;
  const { analyzePullRequest } = await import("../analyzer");
  const out: Record<string, object> = {};
  try {
    for (const spec of SPECS) {
      const repo = path.join(root, spec.name);
      mkdirSync(repo);
      sh(["init", "-q", "-b", "main"], repo);
      sh(["config", "user.email", "golden@ignition.invalid"], repo);
      sh(["config", "user.name", "golden"], repo);
      writeAll(repo, spec.base);
      sh(["add", "-A"], repo); sh(["commit", "-qm", "base"], repo);
      const base = sh(["rev-parse", "HEAD"], repo).trim();
      writeAll(repo, spec.head);
      sh(["add", "-A"], repo); sh(["commit", "-qm", "head"], repo);
      const head = sh(["rev-parse", "HEAD"], repo).trim();
      sh(["update-ref", `refs/pull/${spec.prNumber}/head`, head], repo); // as GitHub has it

      // Every spec is "acme/widgets", and the analyzer keys its mirror by
      // repo name, so each gets its own workspaces root.
      process.env.AST_WORKSPACES_ROOT = path.join(root, `ws-${spec.name}`);

      const payload = await analyzePullRequest({
        repoFullName: "acme/widgets", prNumber: spec.prNumber, baseRef: base,
        source: { type: "git", url: `file://${repo}`, ref: head },
      });
      out[spec.name] = {
        generated_by: GENERATED_BY,
        diff_text: sh(["diff", "--no-color", base, head], repo),
        ast_payload: payload,
      };
    }
  } finally {
    if (previousRoot === undefined) delete process.env.AST_WORKSPACES_ROOT;
    else process.env.AST_WORKSPACES_ROOT = previousRoot;
    rmSync(root, { recursive: true, force: true });
  }
  return out;
}

if (import.meta.main) {
  mkdirSync(OUT_DIR, { recursive: true });
  for (const [name, record] of Object.entries(await generate())) {
    writeFileSync(path.join(OUT_DIR, `${name}.json`), JSON.stringify(record, null, 2) + "\n");
    console.log(`wrote tests/eval/real/${name}.json`);
  }
}
