/**
 * Centralized, deterministic Query Key Factory for TanStack Query.
 */

export const queryKeys = {
  auth: {
    me: () => ["auth", "me"] as const,
  },
  dashboard: {
    stats: () => ["dashboard", "stats"] as const,
  },
  repos: {
    all: () => ["repos"] as const,
    list: () => ["repos", "list"] as const,
    detail: (repoId: string) => ["repos", "detail", repoId] as const,
    settings: (repoId: string) => ["repos", "settings", repoId] as const,
    reviews: (repoFullName: string, page: number, pageSize: number) =>
      ["repos", "reviews", repoFullName, page, pageSize] as const,
  },
  reviews: {
    all: () => ["reviews"] as const,
    list: (filters?: { repo?: string; status?: string; severity?: string; page?: number; pageSize?: number }) =>
      ["reviews", "list", filters ?? {}] as const,
    detail: (reviewId: string) => ["reviews", "detail", reviewId] as const,
  },
  hitl: {
    all: () => ["hitl"] as const,
    pending: () => ["hitl", "pending"] as const,
  },
  ledger: {
    all: () => ["ledger"] as const,
    stats: (repoFullName: string) => ["ledger", "stats", repoFullName] as const,
    trend: (repoFullName: string) => ["ledger", "trend", repoFullName] as const,
  },
} as const
