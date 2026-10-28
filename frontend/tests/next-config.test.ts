/**
 * Audit P0-5: the dashboard calls the API on its own origin and Next.js
 * proxies /api and /auth to the backend, so cookies are first-party
 * (SameSite=Lax works, Safari stops looping) and CORS preflights disappear.
 */
import { afterEach, describe, expect, test, vi } from "vitest"

afterEach(() => {
  vi.unstubAllEnvs()
  vi.resetModules()
})

async function loadConfig() {
  return (await import("../next.config")).default
}

describe("same-origin rewrites (P0-5)", () => {
  test("proxies /api and /auth to BACKEND_INTERNAL_URL", async () => {
    vi.stubEnv("BACKEND_INTERNAL_URL", "https://ignition-backend.internal/")
    const config = await loadConfig()
    expect(config.rewrites).toBeTypeOf("function")
    const rewrites = await config.rewrites!()
    expect(rewrites).toEqual(
      expect.arrayContaining([
        { source: "/api/:path*", destination: "https://ignition-backend.internal/api/:path*" },
        { source: "/auth/:path*", destination: "https://ignition-backend.internal/auth/:path*" },
      ]),
    )
  })

  test("a production build without BACKEND_INTERNAL_URL fails instead of proxying to 'undefined'", async () => {
    vi.stubEnv("BACKEND_INTERNAL_URL", "")
    vi.stubEnv("NODE_ENV", "production")
    const config = await loadConfig()
    expect(config.rewrites).toBeTypeOf("function")
    await expect(config.rewrites!()).rejects.toThrow(/BACKEND_INTERNAL_URL/)
  })
})
