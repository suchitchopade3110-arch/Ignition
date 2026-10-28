/**
 * P2 "CORS preflight on every GET": every request sent
 * Content-Type: application/json, which turns even a bodiless GET into a
 * non-simple request (a CORS preflight before each call while the API was
 * cross-origin). Now the header is set only when there is a body.
 */
import { afterEach, describe, expect, test, vi } from "vitest"

afterEach(() => {
  vi.unstubAllGlobals()
  vi.unstubAllEnvs()
  vi.resetModules()
})

async function sentHeaders(endpoint: string, init?: RequestInit): Promise<Headers> {
  vi.stubEnv("NEXT_PUBLIC_API_URL", "/api")
  vi.stubEnv("NEXT_PUBLIC_DEMO_MODE", "false")
  const fetchMock = vi.fn(async () => new Response(JSON.stringify({ ok: true }), { status: 200 }))
  vi.stubGlobal("fetch", fetchMock)
  const { apiClient } = await import("../src/lib/api-client")
  await apiClient.request(endpoint, init)
  const call = fetchMock.mock.calls[0] as unknown as [string, RequestInit]
  return new Headers(call[1].headers)
}

describe("Content-Type only with a body (P2)", () => {
  test("a GET sends no Content-Type", async () => {
    const headers = await sentHeaders("/stats")
    expect(headers.has("content-type")).toBe(false)
  })

  test("a bodiless POST sends no Content-Type", async () => {
    const headers = await sentHeaders("/hitl/abc/approve", { method: "POST" })
    expect(headers.has("content-type")).toBe(false)
  })

  test("a request with a JSON body sends application/json", async () => {
    const headers = await sentHeaders("/repos/1/settings", { method: "PATCH", body: JSON.stringify({ a: 1 }) })
    expect(headers.get("content-type")).toBe("application/json")
  })

  test("a caller's own Content-Type wins", async () => {
    const headers = await sentHeaders("/x", { method: "POST", body: "a=1", headers: { "Content-Type": "text/plain" } })
    expect(headers.get("content-type")).toBe("text/plain")
  })
})
