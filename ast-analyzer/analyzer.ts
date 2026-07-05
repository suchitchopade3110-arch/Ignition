/**
 * ts-morph AST core tracking logic. Wraps the real TypeScript compiler for
 * true type resolution and cross-file import tracking — a syntax-only
 * parser (tree-sitter) can't do this.
 *
 * Output shape must stay in lockstep with
 * app/schemas/ast_payload.py:ASTAnalyzerPayload — this is the PRD-flagged
 * schema-drift risk. Prefer generating one from the other over hand-syncing.
 */
import { Project } from "ts-morph";
import { existsSync } from "node:fs";
import path from "node:path";

import { prepareSource, type AnalyzeSource } from "./source";

interface AnalyzeArgs {
  repoFullName: string;
  prNumber: number;
  source: AnalyzeSource;
  projectCache: Map<string, Project>;
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

export interface ASTAnalyzerPayload {
  repo_full_name: string;
  pr_number: number;
  changed_files: string[];
  symbols: SymbolRef[];
  dependency_graph: DependencyEdge[];
  hard_rule_violations: string[];
}

// Deterministic hard-rule violations — no LLM, checked against raw source
// text. Keep this list small and unambiguous; anything requiring judgment
// belongs to Agent 2A/2C's semantic checks instead.
const BANNED_PATTERNS = ["eval(", "child_process.exec("];

const GLOB_EXTENSIONS = ["ts", "tsx", "js", "jsx"];

function globsFor(sourceDir: string): string[] {
  return [
    ...GLOB_EXTENSIONS.map((ext) => path.join(sourceDir, "**", `*.${ext}`)),
    `!${path.join(sourceDir, "**", "node_modules", "**")}`,
    `!${path.join(sourceDir, "**", ".git", "**")}`,
  ];
}

function getOrCreateProject(
  repoKey: string,
  sourceDir: string,
  cache: Map<string, Project>
): Project {
  const cached = cache.get(repoKey);
  if (cached) {
    // Refresh: pick up any files added/removed since the last analysis
    // of this repo, without discarding the warm Project/type-checker state.
    cached.addSourceFilesAtPaths(globsFor(sourceDir));
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
  return project;
}

export async function analyzePullRequest(args: AnalyzeArgs): Promise<ASTAnalyzerPayload> {
  const repoKey = args.repoFullName;
  const sourceDir = await prepareSource(repoKey, args.source);
  const project = getOrCreateProject(repoKey, sourceDir, args.projectCache);

  const sourceFiles = project.getSourceFiles();
  const changedFiles: string[] = [];
  const symbols: SymbolRef[] = [];
  const dependencyGraph: DependencyEdge[] = [];
  const hardRuleViolations: string[] = [];

  for (const file of sourceFiles) {
    const relPath = path.relative(sourceDir, file.getFilePath());
    changedFiles.push(relPath);

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
      if (resolved) {
        dependencyGraph.push({
          from_file: relPath,
          to_file: path.relative(sourceDir, resolved.getFilePath()),
          imported_symbols: imp.getNamedImports().map((n) => n.getName()),
        });
      }
    }

    const text = file.getFullText();
    for (const pattern of BANNED_PATTERNS) {
      if (text.includes(pattern)) {
        hardRuleViolations.push(`Banned pattern "${pattern}" found in ${relPath}`);
      }
    }
  }

  return {
    repo_full_name: args.repoFullName,
    pr_number: args.prNumber,
    changed_files: changedFiles,
    symbols,
    dependency_graph: dependencyGraph,
    hard_rule_violations: hardRuleViolations,
  };
}