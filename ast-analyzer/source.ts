/**
 * Resolves an AnalyzeSource into an isolated, per-review directory.
 *
 * Production-readiness changes (audit P0-3, P0-8):
 *  - One shared *mirror* clone per repo (the warm, expensive-to-rebuild part:
 *    network history) plus one throwaway `git worktree` per review, checked
 *    out at the exact head SHA. Two concurrent reviews of the same repo no
 *    longer share — or `checkout --force` over — one working tree.
 *  - Every git operation that mutates the shared mirror (fetch, worktree
 *    add/remove) runs under a per-repo mutex.
 *  - The PR head is fetched explicitly from refs/pull/<n>/head, so fork PRs
 *    don't depend on partial-clone lazy fetching to find the commit.
 *  - Private repos: an installation token is passed via an http.extraHeader
 *    injected through GIT_CONFIG_* env vars — never in the URL, argv, or
 *    the error text this module throws.
 */
import { mkdir, rm } from "node:fs/promises";
import { randomUUID } from "node:crypto";
import path from "node:path";

export type AnalyzeSource =
  | { type: "git"; url: string; ref?: string }
  | { type: "zip"; url: string };

export interface PreparedSource {
  dir: string;
  /** Present for git sources: the shared mirror, for `git diff`/`git show`. */
  gitDir?: string;
  cleanup: () => Promise<void>;
}

export interface GitOptions {
  headSha: string;
  baseSha: string;
  prNumber: number;
  authToken?: string;
}

// Resolved per call (not at import) so tests and deployments can point it
// at a dedicated volume via AST_WORKSPACES_ROOT.
const workspacesRoot = () => process.env.AST_WORKSPACES_ROOT ?? path.join(import.meta.dir, "..", "workspaces");
const mirrorsDir = () => path.join(workspacesRoot(), "mirrors");
const treesDir = () => path.join(workspacesRoot(), "trees");

function safeName(key: string): string {
  return key.replace(/[^a-zA-Z0-9_-]/g, "_");
}

// ---- per-repo mutex ------------------------------------------------------
const locks = new Map<string, Promise<unknown>>();

export async function withRepoLock<T>(key: string, fn: () => Promise<T>): Promise<T> {
  const prev = locks.get(key) ?? Promise.resolve();
  let release!: () => void;
  const next = new Promise<void>((r) => (release = r));
  const chained = prev.then(() => next);
  locks.set(key, chained);
  await prev.catch(() => undefined);
  try {
    return await fn();
  } finally {
    release();
    if (locks.get(key) === chained) locks.delete(key);
  }
}

// ---- git runner ----------------------------------------------------------
function authEnv(token?: string): Record<string, string> {
  if (!token) return {};
  const basic = Buffer.from(`x-access-token:${token}`).toString("base64");
  return {
    GIT_CONFIG_COUNT: "1",
    GIT_CONFIG_KEY_0: "http.extraHeader",
    GIT_CONFIG_VALUE_0: `AUTHORIZATION: basic ${basic}`,
    GIT_TERMINAL_PROMPT: "0",
  };
}

function redact(text: string, token?: string): string {
  return token ? text.split(token).join("***") : text;
}

export async function git(args: string[], cwd: string, token?: string): Promise<string> {
  const proc = Bun.spawn(["git", ...args], {
    cwd,
    stdout: "pipe",
    stderr: "pipe",
    env: { ...process.env, ...authEnv(token) },
  });
  const [out, err, code] = await Promise.all([
    new Response(proc.stdout).text(),
    new Response(proc.stderr).text(),
    proc.exited,
  ]);
  if (code !== 0) {
    throw new Error(`git ${args[0]} failed (exit ${code}): ${redact(err, token).slice(0, 500)}`);
  }
  return out;
}

async function exists(p: string): Promise<boolean> {
  return Bun.file(path.join(p, "HEAD")).exists();
}

async function prepareGitSource(repoKey: string, url: string, opts: GitOptions): Promise<PreparedSource> {
  const mirrors = mirrorsDir();
  const trees = treesDir();
  await mkdir(mirrors, { recursive: true });
  await mkdir(trees, { recursive: true });
  const mirror = path.join(mirrors, `${safeName(repoKey)}.git`);
  const tree = path.join(trees, `${safeName(repoKey)}-${opts.prNumber}-${randomUUID().slice(0, 8)}`);

  await withRepoLock(repoKey, async () => {
    if (!(await exists(mirror))) {
      await git(["clone", "--bare", "--filter=blob:none", "--no-tags", url, mirror], workspacesRoot(), opts.authToken);
    }
    // Branches (for the base), then this PR's head ref explicitly so fork
    // PRs never depend on partial-clone lazy fetching. GitHub always
    // publishes refs/pull/<n>/head; other remotes may not, so that one
    // fetch is allowed to fail as long as the head commit ends up present.
    await git(
      ["fetch", "--no-tags", "--prune", "--update-head-ok", "--filter=blob:none", "origin", "+refs/heads/*:refs/heads/*"],
      mirror,
      opts.authToken,
    );
    await git(
      ["fetch", "--no-tags", "--filter=blob:none", "origin", `+refs/pull/${opts.prNumber}/head:refs/ignition/pull/${opts.prNumber}`],
      mirror,
      opts.authToken,
    ).catch((e) => console.warn(`pull ref fetch skipped: ${String(e).slice(0, 200)}`));
    await git(["cat-file", "-e", `${opts.headSha}^{commit}`], mirror, opts.authToken);
    await git(["cat-file", "-e", `${opts.baseSha}^{commit}`], mirror, opts.authToken);
    await git(["worktree", "add", "--detach", "--force", tree, opts.headSha], mirror, opts.authToken);
  });

  return {
    dir: tree,
    gitDir: mirror,
    cleanup: () =>
      withRepoLock(repoKey, async () => {
        await git(["worktree", "remove", "--force", tree], mirror).catch(() => rm(tree, { recursive: true, force: true }));
        await git(["worktree", "prune"], mirror).catch(() => undefined);
      }),
  };
}

async function prepareZipSource(repoKey: string, url: string): Promise<PreparedSource> {
  const dir = path.join(treesDir(), `${safeName(repoKey)}-zip-${randomUUID().slice(0, 8)}`);
  await mkdir(dir, { recursive: true });
  const zipPath = path.join(dir, "_source.zip");
  const response = await fetch(url);
  if (!response.ok) throw new Error(`Failed to download zip: ${response.status}`);
  await Bun.write(zipPath, response);
  const proc = Bun.spawn(["unzip", "-q", "-o", zipPath, "-d", dir]);
  if ((await proc.exited) !== 0) throw new Error("unzip failed");
  await rm(zipPath);
  return { dir, cleanup: () => rm(dir, { recursive: true, force: true }) };
}

export async function prepareSource(
  repoKey: string,
  source: AnalyzeSource,
  gitOpts?: GitOptions,
): Promise<PreparedSource> {
  if (source.type === "git") {
    if (!gitOpts) throw new Error("git sources require headSha/baseSha/prNumber");
    return prepareGitSource(repoKey, source.url, gitOpts);
  }
  return prepareZipSource(repoKey, source.url);
}
