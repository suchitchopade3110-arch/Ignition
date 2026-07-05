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
    const { repo_full_name, pr_number, source } = body as {
      repo_full_name: string;
      pr_number: number;
      source: AnalyzeSource;
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
        projectCache,
      });
    } catch (err) {
      set.status = 500;
      return { error: err instanceof Error ? err.message : String(err) };
    }
  })
  .get("/healthz", () => ({ status: "ok" }))
  .listen(4000);

console.log(`AST analyzer service listening on :${app.server?.port}`);