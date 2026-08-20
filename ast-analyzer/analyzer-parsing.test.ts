/**
 * Coverage for the actual AST parsing/symbol-extraction logic
 * (analyzer.ts::extractProjectData, detectHardRuleViolations, diffPackages)
 * — everything analyzer.test.ts didn't cover, which was only the project
 * cache's LRU bookkeeping. Every downstream agent treats this analyzer's
 * output as ground truth, so a silent regression here (a symbol kind
 * mis-tagged, an import edge dropped, a hard-rule false positive/negative)
 * would poison every review built on top of it without any test catching
 * it.
 *
 * Uses ts-morph's in-memory file system (no real files, no git/zip
 * source) so these run fast and deterministically — see
 * extractProjectData's doc comment for why it was split out of
 * analyzePullRequest specifically to make this possible.
 */
import { describe, expect, test } from "bun:test";
import { Project } from "ts-morph";

import { detectHardRuleViolations, diffPackages, extractProjectData } from "./analyzer";

const SOURCE_DIR = "/repo";

function projectWithFiles(files: Record<string, string>): Project {
  const project = new Project({ useInMemoryFileSystem: true });
  for (const [relPath, content] of Object.entries(files)) {
    project.createSourceFile(`${SOURCE_DIR}/${relPath}`, content);
  }
  return project;
}

describe("extractProjectData — symbol extraction", () => {
  test("extracts a top-level function with its name, kind and line", () => {
    const project = projectWithFiles({
      "a.ts": `\nexport function greet(name: string) {\n  return "hi " + name;\n}\n`,
    });
    const { symbols } = extractProjectData(project, SOURCE_DIR);

    expect(symbols).toContainEqual({
      file_path: "a.ts",
      symbol_name: "greet",
      kind: "function",
      line: 2,
    });
  });

  test("extracts classes, interfaces, type aliases and variables with the right kind tags", () => {
    const project = projectWithFiles({
      "b.ts": [
        "export class Widget {}",
        "export interface HasId { id: string }",
        "export type Id = string;",
        "export const count = 1;",
      ].join("\n"),
    });
    const { symbols } = extractProjectData(project, SOURCE_DIR);
    const kindsByName = Object.fromEntries(symbols.map((s) => [s.symbol_name, s.kind]));

    expect(kindsByName["Widget"]).toBe("class");
    expect(kindsByName["HasId"]).toBe("interface");
    expect(kindsByName["Id"]).toBe("type");
    expect(kindsByName["count"]).toBe("variable");
  });

  test("tags an anonymous default-exported function instead of dropping it", () => {
    const project = projectWithFiles({
      "c.ts": `export default function (x: number) {\n  return x + 1;\n}\n`,
    });
    const { symbols } = extractProjectData(project, SOURCE_DIR);

    expect(symbols).toContainEqual(
      expect.objectContaining({ symbol_name: "<anonymous>", kind: "function" })
    );
  });

  test("reports file_path relative to the source dir, not an absolute path", () => {
    const project = projectWithFiles({ "nested/deep/file.ts": "export const x = 1;" });
    const { changedFiles, symbols } = extractProjectData(project, SOURCE_DIR);

    expect(changedFiles).toContain("nested/deep/file.ts");
    expect(symbols[0]?.file_path).toBe("nested/deep/file.ts");
  });
});

describe("extractProjectData — dependency graph", () => {
  test("records an edge for an import that resolves to another project file", () => {
    const project = projectWithFiles({
      "utils.ts": "export function helper() {}",
      "main.ts": `import { helper } from "./utils";\nhelper();\n`,
    });
    const { dependencyGraph } = extractProjectData(project, SOURCE_DIR);

    expect(dependencyGraph).toContainEqual({
      from_file: "main.ts",
      to_file: "utils.ts",
      imported_symbols: ["helper"],
    });
  });

  test("does not record an edge for an import that doesn't resolve (e.g. a bare npm package)", () => {
    const project = projectWithFiles({
      "main.ts": `import { z } from "zod";\n`,
    });
    const { dependencyGraph } = extractProjectData(project, SOURCE_DIR);

    expect(dependencyGraph).toEqual([]);
  });

  test("captures multiple named imports from the same edge", () => {
    const project = projectWithFiles({
      "utils.ts": "export function a() {}\nexport function b() {}",
      "main.ts": `import { a, b } from "./utils";\n`,
    });
    const { dependencyGraph } = extractProjectData(project, SOURCE_DIR);

    expect(dependencyGraph[0]?.imported_symbols.sort()).toEqual(["a", "b"]);
  });
});

describe("detectHardRuleViolations", () => {
  test("flags a bare eval() call", () => {
    const project = projectWithFiles({ "a.ts": `eval("2 + 2");` });
    const file = project.getSourceFileOrThrow(`${SOURCE_DIR}/a.ts`);

    const violations = detectHardRuleViolations(file, "a.ts");
    expect(violations).toEqual(["Direct eval() call found in a.ts:1"]);
  });

  test("does not flag a function merely named eval-like (myEval) or eval as a property access", () => {
    const project = projectWithFiles({
      "a.ts": `function myEval() {}\nmyEval();\nconst obj = { eval: () => {} };\nobj.eval();\n`,
    });
    const file = project.getSourceFileOrThrow(`${SOURCE_DIR}/a.ts`);

    expect(detectHardRuleViolations(file, "a.ts")).toEqual([]);
  });

  test("does not flag the string 'eval(' appearing in a comment or string literal", () => {
    const project = projectWithFiles({
      "a.ts": `// banned: eval(\nconst bannedCalls = ["eval("];\n`,
    });
    const file = project.getSourceFileOrThrow(`${SOURCE_DIR}/a.ts`);

    expect(detectHardRuleViolations(file, "a.ts")).toEqual([]);
  });

  test("flags child_process.exec() and the common cp alias", () => {
    const project = projectWithFiles({
      "a.ts": `import * as child_process from "child_process";\nimport * as cp from "child_process";\nchild_process.exec("ls");\ncp.exec("ls");\n`,
    });
    const file = project.getSourceFileOrThrow(`${SOURCE_DIR}/a.ts`);

    const violations = detectHardRuleViolations(file, "a.ts");
    expect(violations).toHaveLength(2);
    expect(violations[0]).toContain("child_process.exec() call found in a.ts");
  });

  test("does not flag .exec() on an unrelated object (e.g. a regex)", () => {
    const project = projectWithFiles({
      "a.ts": `const pattern = /abc/;\npattern.exec("abcdef");\n`,
    });
    const file = project.getSourceFileOrThrow(`${SOURCE_DIR}/a.ts`);

    expect(detectHardRuleViolations(file, "a.ts")).toEqual([]);
  });
});

describe("diffPackages", () => {
  test("reports a package present in head but absent from base as changed", () => {
    const changed = diffPackages({}, { lodash: "^4.17.21" });
    expect(changed).toEqual([{ name: "lodash", version: "4.17.21" }]);
  });

  test("reports a version bump as changed", () => {
    const changed = diffPackages({ lodash: "^4.17.20" }, { lodash: "^4.17.21" });
    expect(changed).toEqual([{ name: "lodash", version: "4.17.21" }]);
  });

  test("does not report an unchanged package", () => {
    const changed = diffPackages({ lodash: "^4.17.21" }, { lodash: "^4.17.21" });
    expect(changed).toEqual([]);
  });

  test("does not report a package removed in head (only additions/changes surface here)", () => {
    const changed = diffPackages({ lodash: "^4.17.21" }, {});
    expect(changed).toEqual([]);
  });

  test("treats every head package as changed when there is no base to compare against", () => {
    const changed = diffPackages(null, { lodash: "^4.17.21", axios: "1.6.0" });
    expect(changed.map((c) => c.name).sort()).toEqual(["axios", "lodash"]);
  });

  test("returns an empty list when head is null (e.g. no package.json at the target ref)", () => {
    expect(diffPackages({ lodash: "^4.17.21" }, null)).toEqual([]);
  });

  test("strips a leading ^ or ~ range specifier from the reported version", () => {
    expect(diffPackages({}, { a: "^1.0.0", b: "~2.0.0" })).toEqual([
      { name: "a", version: "1.0.0" },
      { name: "b", version: "2.0.0" },
    ]);
  });
});
