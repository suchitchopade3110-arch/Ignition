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
function detectHardRuleViolations(file: ReturnType<Project["getSourceFiles"]>[number], relPath: string): string[] {
  const violations: string[] = [];
  const callExpressions = file.getDescendantsOfKind(SyntaxKind.CallExpression);

  for (const call of callExpressions) {
    const line = call.getStartLineNumber();
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

function getOrCreateProject(
  repoKey: string,
  sourceDir: string,
  cache: Map<string, Project>
): Project {
  const cached = cache.get(repoKey);
  if (cached) {
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

    hardRuleViolations.push(...detectHardRuleViolations(file, relPath));
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