/**
 * Persistent Bun HTTP service holding a warm ts-morph Project cache per
 * repo. This resolves the PRD's "subprocess vs. persistent service" open
 * decision in favor of persistent: spawning a fresh process per PR would
 * re-pay full Project initialization (tsconfig resolution, module graph)
 * every time.
 *
 * FastAPI's ast_client.py calls POST /analyze on this service, passing a
 * `source` describing where to fetch code from: either a public git
 * remote (HTTPS recommended — SSH requires a mounted key) or a zip URL.
 */
import { Elysia } from "elysia";
import type { Project } from "ts-morph";
import { analyzePullRequest } from "./analyzer";
import type { AnalyzeSource } from "./source";

const projectCache = new Map<string, Project>();

const app = new Elysia()
  .post("/analyze", async ({ body, set }) => {
    const { repo_full_name, pr_number, source, base_sha } = body as {
      repo_full_name: string;
      pr_number: number;
      source: AnalyzeSource;
      base_sha: string;
    };

    if (!source || (source.type !== "git" && source.type !== "zip")) {
      set.status = 422;
      return { error: "source must be { type: 'git', url, ref? } or { type: 'zip', url }" };
    }

    try {
      return await analyzePullRequest({
        repoFullName: repo_full_name,
        prNumber: pr_number,
        source,
        baseRef: base_sha,
        projectCache,
      });
    } catch (err) {
      set.status = 500;
      return { error: err instanceof Error ? err.message : String(err) };
    }
  })
  .get("/healthz", () => ({ status: "ok" }))
  .listen({
    port: 4000,
    // Default to loopback-only (single-container mode: docker-entrypoint.sh
    // runs this as a sibling process of FastAPI/the Arq worker in the same
    // container — same reasoning as the original Phase 1 fix, nothing
    // outside that container has any legitimate reason to reach /analyze,
    // which takes a raw git/zip URL to clone with no auth of its own).
    //
    // docker-compose.yml's multi-container topology (Phase 2) is the one
    // place this is overridden to 0.0.0.0 via AST_ANALYZER_HOST — there,
    // the worker/backend containers are on a different network namespace
    // than this one, so loopback would make this unreachable even to
    // legitimate sibling containers. The trust boundary shifts from "bound
    // to loopback" to "Docker's private compose network with no published
    // host port" — see the comment on the ast-analyzer service in
    // docker-compose.yml for why that's an equivalent boundary, not a
    // weaker one.
    hostname: process.env.AST_ANALYZER_HOST || "127.0.0.1",
  });

console.log(`AST analyzer service listening on ${process.env.AST_ANALYZER_HOST || "127.0.0.1"}:${app.server?.port}`);