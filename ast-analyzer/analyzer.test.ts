/**
 * Coverage for the per-repo warm ts-morph Project cache's LRU eviction
 * (analyzer.ts::getOrCreateProject / evictLeastRecentlyUsed) — added after
 * the deployment-readiness review flagged the cache as unbounded. Uses
 * empty temp directories as "source dirs" so Project construction stays
 * cheap (no real repo content needed to exercise cache bookkeeping).
 */
import { afterEach, beforeEach, describe, expect, test } from "bun:test";
import { mkdtempSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";
import type { Project } from "ts-morph";

import { getOrCreateProject } from "./analyzer";

let tmpDirs: string[] = [];

function freshSourceDir(): string {
  const dir = mkdtempSync(path.join(tmpdir(), "ast-analyzer-test-"));
  tmpDirs.push(dir);
  return dir;
}

beforeEach(() => {
  tmpDirs = [];
});

afterEach(() => {
  for (const dir of tmpDirs) {
    rmSync(dir, { recursive: true, force: true });
  }
  delete process.env.AST_CACHE_MAX_PROJECTS;
});

describe("getOrCreateProject cache eviction", () => {
  test("reuses the same Project instance for the same repo key", () => {
    const cache = new Map<string, Project>();
    const dir = freshSourceDir();

    const first = getOrCreateProject("acme/widgets", dir, cache);
    const second = getOrCreateProject("acme/widgets", dir, cache);

    expect(second).toBe(first);
    expect(cache.size).toBe(1);
  });

  test("evicts the least-recently-used entry once over the configured limit", () => {
    process.env.AST_CACHE_MAX_PROJECTS = "2";
    const cache = new Map<string, Project>();

    getOrCreateProject("repo/a", freshSourceDir(), cache);
    getOrCreateProject("repo/b", freshSourceDir(), cache);
    getOrCreateProject("repo/c", freshSourceDir(), cache); // pushes cache over the limit

    expect(cache.size).toBe(2);
    expect(cache.has("repo/a")).toBe(false); // oldest, evicted
    expect(cache.has("repo/b")).toBe(true);
    expect(cache.has("repo/c")).toBe(true);
  });

  test("re-accessing an entry marks it recently used, protecting it from eviction", () => {
    process.env.AST_CACHE_MAX_PROJECTS = "2";
    const cache = new Map<string, Project>();
    const dirA = freshSourceDir();

    getOrCreateProject("repo/a", dirA, cache);
    getOrCreateProject("repo/b", freshSourceDir(), cache);
    // Touch "repo/a" again — without this it would be the LRU victim next.
    getOrCreateProject("repo/a", dirA, cache);
    getOrCreateProject("repo/c", freshSourceDir(), cache); // "repo/b" is now the LRU one

    expect(cache.size).toBe(2);
    expect(cache.has("repo/a")).toBe(true);
    expect(cache.has("repo/b")).toBe(false);
    expect(cache.has("repo/c")).toBe(true);
  });

  test("defaults to a bounded limit when AST_CACHE_MAX_PROJECTS is unset", () => {
    const cache = new Map<string, Project>();
    for (let i = 0; i < 30; i++) {
      getOrCreateProject(`repo/${i}`, freshSourceDir(), cache);
    }
    // DEFAULT_MAX_CACHED_PROJECTS is 25 — this just asserts *some* bound
    // is enforced without hardcoding the exact default in two places.
    expect(cache.size).toBeLessThan(30);
    expect(cache.size).toBeGreaterThan(0);
  });
});
