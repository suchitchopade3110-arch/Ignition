/**
 * Resolves an AnalyzeSource (git URL or zip URL) into a local directory
 * ts-morph can read from. Kept separate from analyzer.ts so the "how do
 * we get the code" concern doesn't tangle with the "how do we read the
 * AST" concern.
 *
 * NOTE on git sources: only HTTPS clone is truly credential-free for
 * public repos. SSH URLs (git@github.com:... or ssh://...) require a
 * mounted SSH key regardless of repo visibility — GitHub does not permit
 * anonymous SSH clones. If you pass an SSH URL without key access
 * configured on this container, the clone will fail; that's expected.
 */
import { mkdir, rm } from "node:fs/promises";
import path from "node:path";

export type AnalyzeSource =
  | { type: "git"; url: string; ref?: string }
  | { type: "zip"; url: string };

const WORKSPACES_ROOT = path.join(import.meta.dir, "..", "workspaces");

function workspaceDirFor(key: string): string {
  // Stable, reusable directory per repo. This is what makes re-analysis
  // fast: a git fetch+reset (or fresh unzip) instead of a cold clone
  // every time, in keeping with the PRD's "warm cache" design goal.
  const safe = key.replace(/[^a-zA-Z0-9_-]/g, "_");
  return path.join(WORKSPACES_ROOT, safe);
}

async function run(cmd: string[], cwd?: string): Promise<void> {
  const proc = Bun.spawn(cmd, { cwd, stdout: "pipe", stderr: "pipe" });
  const exitCode = await proc.exited;
  if (exitCode !== 0) {
    const stderr = await new Response(proc.stderr).text();
    throw new Error(`Command failed (${cmd.join(" ")}): ${stderr}`);
  }
}

async function isGitRepo(dir: string): Promise<boolean> {
  return Bun.file(path.join(dir, ".git", "HEAD")).exists();
}

async function prepareGitSource(repoKey: string, url: string, ref?: string): Promise<string> {
  const dir = workspaceDirFor(repoKey);
  await mkdir(WORKSPACES_ROOT, { recursive: true });

  if (await isGitRepo(dir)) {
    await run(["git", "fetch", "--all", "--prune"], dir);
  } else {
    // --filter=blob:none: partial clone, fetches file contents lazily.
    // Faster than --depth=1 when we need to check out an arbitrary SHA
    // (shallow clones can't check out commits outside the shallow window).
    await run(["git", "clone", "--filter=blob:none", url, dir]);
  }

  if (ref) {
    await run(["git", "checkout", "--force", ref], dir);
  }

  return dir;
}

async function prepareZipSource(repoKey: string, url: string): Promise<string> {
  const dir = workspaceDirFor(repoKey);
  await mkdir(dir, { recursive: true });

  const zipPath = path.join(dir, "_source.zip");
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`Failed to download zip from ${url}: ${response.status} ${response.statusText}`);
  }
  await Bun.write(zipPath, response);

  // Clear stale extracted contents from a previous run before re-extracting,
  // so deleted files in the new zip don't linger as ghosts in the workspace.
  await run(["bash", "-c", `find "${dir}" -mindepth 1 ! -name "_source.zip" -exec rm -rf {} +`]);
  await run(["unzip", "-q", "-o", zipPath, "-d", dir]);
  await rm(zipPath);

  return dir;
}

export async function prepareSource(repoKey: string, source: AnalyzeSource): Promise<string> {
  if (source.type === "git") {
    return prepareGitSource(repoKey, source.url, source.ref);
  }
  return prepareZipSource(repoKey, source.url);
}
