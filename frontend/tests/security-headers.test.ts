/**
 * P2 "No CSP or security headers": next.config.ts now sends the solutions
 * doc's Content-Security-Policy, nosniff, Referrer-Policy and HSTS.
 * connect-src 'self' is enough because the API is same-origin (P0-5).
 */
import { readdirSync, readFileSync, statSync } from "node:fs"
import path from "node:path"
import { afterEach, describe, expect, test, vi } from "vitest"

afterEach(() => {
  vi.resetModules()
})

const CSP =
  "default-src 'self'; img-src 'self' data: https://avatars.githubusercontent.com; " +
  "script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; connect-src 'self'; " +
  "frame-ancestors 'none'; base-uri 'self'; form-action 'self' https://github.com"

type Rule = { source: string; headers: { key: string; value: string }[] }

async function rules(): Promise<Rule[]> {
  const config = (await import("../next.config")).default
  expect(config.headers).toBeTypeOf("function")
  return (await config.headers!()) as Rule[]
}

function headersFor(all: Rule[], path: string): Record<string, string> {
  const out: Record<string, string> = {}
  for (const rule of all) {
    // Next matches `source` as a path-to-regexp pattern; these rules only use
    // a "/(regex)" group, which this mirrors.
    const m = /^\/\((.*)\)$/.exec(rule.source)
    if (!m || !new RegExp(`^${m[1]}$`).test(path.slice(1))) continue
    for (const h of rule.headers) out[h.key] = h.value
  }
  return out
}

describe("security headers (P2)", () => {
  test("every app page gets the doc's CSP and the three other headers", async () => {
    const all = await rules()
    for (const path of ["/", "/dashboard", "/reviews/abc", "/api/stats"]) {
      expect(headersFor(all, path)).toEqual({
        "Content-Security-Policy": CSP,
        "X-Content-Type-Options": "nosniff",
        "Referrer-Policy": "strict-origin-when-cross-origin",
        "Strict-Transport-Security": "max-age=63072000; includeSubDomains",
      })
    }
  })

  test("the proxied API docs keep the other headers but not the CSP (Swagger UI loads from a CDN)", async () => {
    const all = await rules()
    for (const path of ["/docs", "/redoc"]) {
      const h = headersFor(all, path)
      expect(h["Content-Security-Policy"]).toBeUndefined()
      expect(h["X-Content-Type-Options"]).toBe("nosniff")
      expect(h["Strict-Transport-Security"]).toBe("max-age=63072000; includeSubDomains")
    }
  })
})

function sourceFiles(dir: string): string[] {
  return readdirSync(dir).flatMap((name) => {
    const full = path.join(dir, name)
    return statSync(full).isDirectory() ? sourceFiles(full) : /\.(ts|tsx)$/.test(name) ? [full] : []
  })
}

test("no client code fetches another origin, which connect-src 'self' would block", () => {
  const offenders = sourceFiles(path.join(__dirname, "../src")).filter((file) =>
    /fetch\(\s*["'`]https?:\/\//.test(readFileSync(file, "utf8")),
  )
  expect(offenders).toEqual([])
})
