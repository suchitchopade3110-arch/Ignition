/**
 * ts-morph AST core tracking logic. Wraps the real TypeScript compiler for
 * true type resolution and cross-file import tracking — a syntax-only
 * parser (tree-sitter) can't do this.
 *
 * Output shape must stay in lockstep with
 * app/schemas/ast_payload.py:ASTAnalyzerPayload — this is the PRD-flagged
 * schema-drift risk. Prefer generating one from the other over hand-syncing.
 */
import { Project, SyntaxKind, Node } from "ts-morph";
import { existsSync } from "node:fs";
import path from "node:path";

import { prepareSource, git, type AnalyzeSource } from "./source";

interface AnalyzeArgs {
  repoFullName: string;
  prNumber: number;
  source: AnalyzeSource;
  baseRef: string;
  /** Short-lived GitHub installation token for private repos. Never logged. */
  authToken?: string;
  /** Kept for signature compatibility; no longer used (fresh Project per review). */
  projectCache?: Map<string, Project>;
}

interface SymbolRef {
  file_path: string;
  symbol_name: string;
  kind: string;
  line: number;
}

interface DependencyEdge {
  from_file: string;
  to_file: string;
  imported_symbols: string[];
}

interface PackageRef {
  name: string;
  version: string;
}

export interface ASTAnalyzerPayload {
  repo_full_name: string;
  pr_number: number;
  changed_files: string[];
  symbols: SymbolRef[];
  dependency_graph: DependencyEdge[];
  hard_rule_violations: string[];
  changed_packages: PackageRef[];  // NEW
}

const GLOB_EXTENSIONS = ["ts", "tsx", "js", "jsx"];

function globsFor(sourceDir: string): string[] {
  return [
    ...GLOB_EXTENSIONS.map((ext) => path.join(sourceDir, "**", `*.${ext}`)),
    `!${path.join(sourceDir, "**", "node_modules", "**")}`,
    `!${path.join(sourceDir, "**", ".git", "**")}`,
  ];
}

/**
 * AST-based hard-rule detection — deliberately NOT a text/substring match.
 *
 * A naive `sourceText.includes("eval(")` check flags any file that merely
 * CONTAINS that string, including files that document the pattern (like
 * this very file, or a security-linting config listing banned calls) —
 * a real false positive discovered in production testing. Checking actual
 * CallExpression nodes means only genuine invocations are flagged; string
 * literals, comments, and pattern-definition arrays are structurally
 * invisible to this check, since they're never parsed as call expressions.
 */
export function detectHardRuleViolations(
  file: ReturnType<Project["getSourceFiles"]>[number],
  relPath: string,
  addedLines?: Set<number>,
): string[] {
  const violations: string[] = [];
  const callExpressions = file.getDescendantsOfKind(SyntaxKind.CallExpression);

  for (const call of callExpressions) {
    const line = call.getStartLineNumber();
    // P0-2: only lines this PR added can "introduce" a violation.
    if (addedLines && !addedLines.has(line)) continue;
    const expr = call.getExpression();

    // Direct eval(...) call — matches only a bare identifier named "eval",
    // not "myEval(" or a property like "obj.eval(".
    if (Node.isIdentifier(expr) && expr.getText() === "eval") {
      violations.push(`Direct eval() call found in ${relPath}:${line}`);
      continue;
    }

    // child_process.exec(...) / cp.exec(...) — property access where the
    // method name is "exec" and the object side plausibly refers to the
    // child_process module (imported as child_process, cp, or via a
    // require('child_process') call).
    if (Node.isPropertyAccessExpression(expr) && expr.getName() === "exec") {
      const objectText = expr.getExpression().getText();
      const looksLikeChildProcess =
        objectText === "child_process" ||
        objectText === "cp" ||
        objectText.includes("require('child_process')") ||
        objectText.includes('require("child_process")');

      if (looksLikeChildProcess) {
        violations.push(`child_process.exec() call found in ${relPath}:${line}`);
      }
    }
  }

  return violations;
}

// Unbounded before this — projectCache (a Map, module-level in server.ts,
// living for the process's whole lifetime) grew by one warm ts-morph
// Project per distinct repo ever analyzed, with no eviction. A long-running
// deployment touching many repos over time would keep every one of them
// resident in memory forever. Bounded LRU eviction below caps that: once
// more than AST_CACHE_MAX_PROJECTS distinct repos are cached, the least
// recently used one is dropped to make room for the next.
const DEFAULT_MAX_CACHED_PROJECTS = 25;

function maxCachedProjects(): number {
  const raw = process.env.AST_CACHE_MAX_PROJECTS;
  const parsed = raw ? Number.parseInt(raw, 10) : NaN;
  return Number.isFinite(parsed) && parsed > 0 ? parsed : DEFAULT_MAX_CACHED_PROJECTS;
}

// Exported for analyzer.test.ts — the LRU eviction behavior is real logic
// worth testing directly rather than only indirectly through the full
// analyzePullRequest pipeline (which needs a real/fake git or zip source).
export function getOrCreateProject(
  repoKey: string,
  sourceDir: string,
  cache: Map<string, Project>
): Project {
  const cached = cache.get(repoKey);
  if (cached) {
    cached.addSourceFilesAtPaths(globsFor(sourceDir));
    // Map preserves insertion order, not access order — re-inserting the
    // same key moves it to the end, which is what makes "the first key in
    // the Map" a valid least-recently-USED (not just least-recently-
    // inserted) victim for eviction below.
    cache.delete(repoKey);
    cache.set(repoKey, cached);
    return cached;
  }

  const tsConfigPath = path.join(sourceDir, "tsconfig.json");
  const hasTsConfig = existsSync(tsConfigPath);

  const project = new Project({
    tsConfigFilePath: hasTsConfig ? tsConfigPath : undefined,
    skipAddingFilesFromTsConfig: !hasTsConfig,
  });

  if (!hasTsConfig) {
    project.addSourceFilesAtPaths(globsFor(sourceDir));
  }

  cache.set(repoKey, project);
  evictLeastRecentlyUsed(cache);
  return project;
}

export function evictLeastRecentlyUsed(cache: Map<string, Project>): void {
  const limit = maxCachedProjects();
  while (cache.size > limit) {
    const oldestKey = cache.keys().next().value;
    if (oldestKey === undefined) break;
    cache.delete(oldestKey);
    console.log(`AST project cache evicted (over ${limit}-entry limit): ${oldestKey}`);
  }
}

interface ExtractedProjectData {
  changedFiles: string[];
  symbols: SymbolRef[];
  dependencyGraph: DependencyEdge[];
  hardRuleViolations: string[];
}

export interface ExtractScope {
  /** Files this PR added/modified (repo-relative, posix). */
  changed: Set<string>;
  /** Added line numbers per changed file, from `git diff -U0`. */
  addedLines: Map<string, Set<number>>;
}

function rel(sourceDir: string, abs: string): string {
  return path.relative(sourceDir, abs).split(path.sep).join("/");
}

// Split out of analyzePullRequest so the symbol/dependency-graph/hard-rule
// walk can be exercised directly against an in-memory ts-morph Project in
// tests, without needing a real git clone or zip download through
// prepareSource — see analyzer.test.ts.
//
// With a `scope` (every git-sourced review), output is limited to the diff
// (audit P0-2): changed_files is exactly the PR's changed files, symbols
// and edges cover changed files plus one hop, and hard rules apply only to
// added lines. Without one (unit tests, zip sources) every file is in scope.
export function extractProjectData(project: Project, sourceDir: string, scope?: ExtractScope): ExtractedProjectData {
  const sourceFiles = project.getSourceFiles();
  const changedFiles: string[] = [];
  const symbols: SymbolRef[] = [];
  const dependencyGraph: DependencyEdge[] = [];
  const hardRuleViolations: string[] = [];

  // One hop of neighbours: files the changed files import, and files that
  // import a changed file.
  let inScope: Set<string> | null = null;
  if (scope) {
    inScope = new Set(scope.changed);
    for (const file of sourceFiles) {
      const from = rel(sourceDir, file.getFilePath());
      for (const imp of file.getImportDeclarations()) {
        const target = imp.getModuleSpecifierSourceFile();
        if (!target) continue;
        const to = rel(sourceDir, target.getFilePath());
        if (scope.changed.has(from)) inScope.add(to);
        if (scope.changed.has(to)) inScope.add(from);
      }
    }
  }

  for (const file of sourceFiles) {
    const relPath = rel(sourceDir, file.getFilePath());
    if (inScope && !inScope.has(relPath)) continue;
    const isChanged = !scope || scope.changed.has(relPath);
    if (isChanged) changedFiles.push(relPath);

    for (const fn of file.getFunctions()) {
      symbols.push({
        file_path: relPath,
        symbol_name: fn.getName() ?? "<anonymous>",
        kind: "function",
        line: fn.getStartLineNumber(),
      });
    }
    for (const cls of file.getClasses()) {
      symbols.push({
        file_path: relPath,
        symbol_name: cls.getName() ?? "<anonymous>",
        kind: "class",
        line: cls.getStartLineNumber(),
      });
    }
    for (const iface of file.getInterfaces()) {
      symbols.push({
        file_path: relPath,
        symbol_name: iface.getName(),
        kind: "interface",
        line: iface.getStartLineNumber(),
      });
    }
    for (const alias of file.getTypeAliases()) {
      symbols.push({
        file_path: relPath,
        symbol_name: alias.getName(),
        kind: "type",
        line: alias.getStartLineNumber(),
      });
    }
    for (const varDecl of file.getVariableDeclarations()) {
      symbols.push({
        file_path: relPath,
        symbol_name: varDecl.getName(),
        kind: "variable",
        line: varDecl.getStartLineNumber(),
      });
    }

    for (const imp of file.getImportDeclarations()) {
      const resolved = imp.getModuleSpecifierSourceFile();
      if (!resolved) continue;
      const to = rel(sourceDir, resolved.getFilePath());
      // Keep only edges that touch the diff (either end changed).
      if (scope && !scope.changed.has(relPath) && !scope.changed.has(to)) continue;
      dependencyGraph.push({
        from_file: relPath,
        to_file: to,
        imported_symbols: imp.getNamedImports().map((n) => n.getName()),
      });
    }

    if (isChanged) {
      hardRuleViolations.push(...detectHardRuleViolations(file, relPath, scope?.addedLines.get(relPath)));
    }
  }

  return { changedFiles, symbols, dependencyGraph, hardRuleViolations };
}

const ANALYZABLE = /\.(ts|tsx|js|jsx|mts|cts|mjs|cjs)$/;

/** Changed files and their added line numbers, from the real git diff. */
export async function diffScope(gitDir: string, baseSha: string, headSha: string, token?: string): Promise<ExtractScope> {
  const names = await git(["diff", "--name-only", "--diff-filter=ACMR", `${baseSha}...${headSha}`], gitDir, token);
  const changed = new Set(names.split("\n").map((s) => s.trim()).filter((s) => s && ANALYZABLE.test(s)));

  const addedLines = new Map<string, Set<number>>();
  const patch = await git(["diff", "-U0", "--diff-filter=ACMR", `${baseSha}...${headSha}`], gitDir, token);
  let current: string | null = null;
  for (const line of patch.split("\n")) {
    if (line.startsWith("+++ ")) {
      current = line.startsWith("+++ b/") ? line.slice(6) : null;
      if (current && !addedLines.has(current)) addedLines.set(current, new Set());
    } else if (current && line.startsWith("@@")) {
      const m = /\+(\d+)(?:,(\d+))?/.exec(line);
      if (!m) continue;
      const startLine = Number(m[1]);
      const count = m[2] === undefined ? 1 : Number(m[2]);
      for (let i = 0; i < count; i++) addedLines.get(current)!.add(startLine + i);
    }
  }
  return { changed, addedLines };
}

function buildProject(sourceDir: string): Project {
  const tsConfigPath = path.join(sourceDir, "tsconfig.json");
  const hasTsConfig = existsSync(tsConfigPath);
  const project = new Project({
    tsConfigFilePath: hasTsConfig ? tsConfigPath : undefined,
    skipAddingFilesFromTsConfig: !hasTsConfig,
  });
  if (!hasTsConfig) project.addSourceFilesAtPaths(globsFor(sourceDir));
  return project;
}

export async function analyzePullRequest(args: AnalyzeArgs): Promise<ASTAnalyzerPayload> {
  const headSha = args.source.type === "git" ? args.source.ref ?? "HEAD" : "HEAD";
  const prepared = await prepareSource(args.repoFullName, args.source, {
    headSha,
    baseSha: args.baseRef,
    prNumber: args.prNumber,
    authToken: args.authToken,
  });

  try {
    // Fresh Project per review, built from this review's own worktree:
    // no stale ASTs (P0-3). The warm part that matters — git history — lives
    // in the shared mirror, so this costs a parse, not a clone.
    const project = buildProject(prepared.dir);
    const scope = prepared.gitDir ? await diffScope(prepared.gitDir, args.baseRef, headSha, args.authToken) : undefined;
    const { changedFiles, symbols, dependencyGraph, hardRuleViolations } = extractProjectData(
      project,
      prepared.dir,
      scope,
    );

    const [basePackages, headPackages] = prepared.gitDir
      ? await Promise.all([
          getPackageJsonAtRef(prepared.gitDir, args.baseRef, args.authToken),
          getPackageJsonAtRef(prepared.gitDir, headSha, args.authToken),
        ])
      : [null, null];

    return {
      repo_full_name: args.repoFullName,
      pr_number: args.prNumber,
      changed_files: changedFiles,
      symbols,
      dependency_graph: dependencyGraph,
      hard_rule_violations: hardRuleViolations,
      changed_packages: diffPackages(basePackages, headPackages),
    };
  } finally {
    await prepared.cleanup();
  }
}

/**
 * Extracts a flat name->version map from package.json at a given git ref,
 * without checking out that ref (uses `git show` directly against the
 * already-cloned repo's history). Returns null if the ref/file doesn't
 * exist — a repo might not have a package.json, or the base ref might
 * predate one being added.
 */
async function getPackageJsonAtRef(
  gitDir: string,
  ref: string,
  token?: string
): Promise<Record<string, string> | null> {
  try {
    const output = await git(["show", `${ref}:package.json`], gitDir, token);
    const pkg = JSON.parse(output);
    return { ...(pkg.dependencies ?? {}), ...(pkg.devDependencies ?? {}) };
  } catch {
    return null;
  }
}

/**
 * Compares two dependency maps and returns packages that are new or
 * whose declared version changed. Doesn't attempt semver resolution —
 * this is intentionally a simple string diff on the declared range,
 * since Agent 2C's job is flagging what to LOOK AT, not resolving exact
 * installed versions (that's what package-lock.json is for, and parsing
 * that is a separate, heavier task not needed for this check).
 */
export function diffPackages(
  base: Record<string, string> | null,
  head: Record<string, string> | null
): { name: string; version: string }[] {
  if (!head) return [];
  const changed: { name: string; version: string }[] = [];

  for (const [name, version] of Object.entries(head)) {
    const baseVersion = base?.[name];
    if (baseVersion !== version) {
      const v = normalizeVersion(version);
      if (v) changed.push(v.alias ? { name: v.alias, version: v.version } : { name, version: v.version });
    }
  }

  return changed;
}

/**
 * Turns a declared range into a concrete version OSV/npm can look up, or
 * null when there isn't one (workspace:, file:, link:, git URLs, tags).
 * `npm:real-pkg@^1.2.3` aliases resolve to the real package name.
 */
export function normalizeVersion(spec: string): { version: string; alias?: string } | null {
  let s = spec.trim();
  let alias: string | undefined;
  if (s.startsWith("npm:")) {
    const at = s.lastIndexOf("@");
    if (at <= 4) return null;
    alias = s.slice(4, at);
    s = s.slice(at + 1);
  }
  if (/^(workspace:|file:|link:|git|github:|https?:)/.test(s) || s.includes("/")) return null;
  const m = /(\d+)(?:\.(\d+|x|\*))?(?:\.(\d+|x|\*))?(-[0-9A-Za-z.-]+)?/.exec(s);
  if (!m) return null;
  const part = (p?: string) => (p === undefined || p === "x" || p === "*" ? "0" : p);
  return { version: `${m[1]}.${part(m[2])}.${part(m[3])}${m[4] ?? ""}`, alias };
}