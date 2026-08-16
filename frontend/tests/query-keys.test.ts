import { describe, it, expect } from "vitest"
import { queryKeys } from "@/lib/query-keys"

describe("queryKeys Factory", () => {
  it("generates deterministic auth and dashboard keys", () => {
    expect(queryKeys.auth.me()).toEqual(["auth", "me"])
    expect(queryKeys.dashboard.stats()).toEqual(["dashboard", "stats"])
  })

  it("generates repository keys with correct scopes", () => {
    expect(queryKeys.repos.all()).toEqual(["repos"])
    expect(queryKeys.repos.list()).toEqual(["repos", "list"])
    expect(queryKeys.repos.settings("repo-123")).toEqual(["repos", "settings", "repo-123"])
    // page/pageSize are part of the key deliberately — different pages
    // must not collide in the cache, or React Query would serve page 1's
    // cached data back for a page 2 request.
    expect(queryKeys.repos.reviews("org/repo", 1, 25)).toEqual(["repos", "reviews", "org/repo", 1, 25])
    expect(queryKeys.repos.reviews("org/repo", 1, 25)).not.toEqual(
      queryKeys.repos.reviews("org/repo", 2, 25)
    )
  })

  it("isolates reviews list and detail keys", () => {
    expect(queryKeys.reviews.all()).toEqual(["reviews"])
    expect(queryKeys.reviews.list()).toEqual(["reviews", "list", {}])
    expect(queryKeys.reviews.list({ status: "running" })).toEqual([
      "reviews",
      "list",
      { status: "running" },
    ])
    expect(queryKeys.reviews.detail("rev-abc")).toEqual(["reviews", "detail", "rev-abc"])
  })

  it("prevents key collisions across different repositories", () => {
    const keyRepoA = queryKeys.repos.settings("repo-a")
    const keyRepoB = queryKeys.repos.settings("repo-b")
    expect(keyRepoA).not.toEqual(keyRepoB)

    const ledgerA = queryKeys.ledger.stats("org/repo-a")
    const ledgerB = queryKeys.ledger.stats("org/repo-b")
    expect(ledgerA).not.toEqual(ledgerB)
  })
})
