/**
 * Audit P0-8 (private repos): the installation token must reach GitHub as
 * an HTTP header injected through GIT_CONFIG_* env vars — never in the
 * clone URL or argv — and must never appear in an error message.
 */
import { afterAll, beforeAll, describe, expect, test } from "bun:test";
import { mkdtempSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";

import { git } from "./source";

const TOKEN = "ghs_SECRET123";
let repoDir: string;

beforeAll(() => {
  repoDir = mkdtempSync(path.join(tmpdir(), "ign-src-"));
  Bun.spawnSync(["git", "init", "-q"], { cwd: repoDir });
});
afterAll(() => rmSync(repoDir, { recursive: true, force: true }));

describe("git() auth and redaction", () => {
  test("sends the token as an Authorization header, not in the URL", async () => {
    let seenAuth = "";
    let seenUrl = "";
    const server = Bun.serve({
      port: 0,
      hostname: "127.0.0.1",
      fetch(req) {
        seenAuth = req.headers.get("authorization") ?? "";
        seenUrl = req.url;
        return new Response("no", { status: 403 });
      },
    });
    try {
      const err = await git(["ls-remote", `http://127.0.0.1:${server.port}/acme/private.git`], repoDir, TOKEN)
        .then(() => "")
        .catch((e) => String(e));
      expect(seenAuth.toLowerCase()).toBe(
        `basic ${Buffer.from(`x-access-token:${TOKEN}`).toString("base64")}`.toLowerCase(),
      );
      expect(seenUrl).not.toContain(TOKEN);
      expect(err).toContain("git ls-remote failed");
      expect(err).not.toContain(TOKEN);
    } finally {
      server.stop(true);
    }
  });

  test("redacts the token from git's own error text", async () => {
    // Precondition: git really does echo an unknown revision back in stderr.
    const raw = Bun.spawnSync(["git", "show", TOKEN], { cwd: repoDir, stderr: "pipe" });
    expect(raw.stderr.toString()).toContain(TOKEN);

    const err = await git(["show", TOKEN], repoDir, TOKEN).then(() => "").catch((e) => String(e));
    expect(err).toContain("git show failed");
    expect(err).not.toContain(TOKEN);
  });
});
