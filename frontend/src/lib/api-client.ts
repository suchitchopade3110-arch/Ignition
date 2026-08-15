/**
 * Hardened Production API Client.
 *
 * Implements:
 * - Centralized configuration from lib/config.ts
 * - 15-second request timeouts via AbortController
 * - Error classification and structured ApiError throwing
 * - Global 401 unauthorized subscriber for session invalidation
 * - Strict isolation of mock development data
 */

import { appConfig } from "./config"
import { ApiError } from "./errors"
import {
  AuthUser,
  DashboardStats,
  HitlItem,
  LedgerStats,
  LedgerTrend,
  Repository,
  RepositorySettings,
  Review,
  ReviewDetail,
} from "@/types"
import {
  mockStats,
  mockHitlPending,
  mockLedgerStats,
  mockLedgerTrend,
  mockRepositories,
  mockRepoSettings,
  mockReviewDetail,
  mockReviews,
} from "./mock/data"

type UnauthorizedHandler = () => void

class ApiClient {
  private unauthorizedHandlers: UnauthorizedHandler[] = []

  /**
   * Register a callback triggered whenever a 401 Unauthorized is received from the server.
   */
  onUnauthorized(handler: UnauthorizedHandler): () => void {
    this.unauthorizedHandlers.push(handler)
    return () => {
      this.unauthorizedHandlers = this.unauthorizedHandlers.filter((h) => h !== handler)
    }
  }

  private notifyUnauthorized(): void {
    this.unauthorizedHandlers.forEach((handler) => {
      try {
        handler()
      } catch (err) {
        console.error("Error in unauthorized handler:", err)
      }
    })
  }

  /**
   * Centralized HTTP request handler with timeout, credentials, and error wrapping.
   */
  async request<T>(
    endpoint: string,
    options: RequestInit = {},
    timeoutMs: number = 15000
  ): Promise<T> {
    const fetchOptions: RequestInit = { ...options }

    // Mock data fallback: ONLY permitted in development when NEXT_PUBLIC_DEMO_MODE=true
    if (appConfig.isMockEnabled()) {
      if (endpoint === "/auth/me") {
        return {
          id: "mock-user-1",
          github_id: 12345,
          login: "demo-engineer",
          name: "Demo Engineer",
          avatar_url: "https://avatars.githubusercontent.com/u/583231?v=4",
        } as unknown as T
      }
      if (endpoint === "/stats") return mockStats as unknown as T
      if (endpoint === "/repos") return mockRepositories as unknown as T
      if (endpoint.startsWith("/repos/") && endpoint.endsWith("/settings")) {
        return mockRepoSettings as unknown as T
      }
      if (endpoint.startsWith("/repos/") && endpoint.endsWith("/reviews")) {
        return mockReviews as unknown as T
      }
      if (endpoint.startsWith("/ledger/") && endpoint.endsWith("/trend")) {
        return mockLedgerTrend as unknown as T
      }
      if (endpoint.startsWith("/ledger/")) {
        return mockLedgerStats as unknown as T
      }
      if (endpoint === "/hitl/pending") return mockHitlPending as unknown as T
      if (endpoint.startsWith("/reviews?")) return mockReviews as unknown as T
      if (endpoint === "/reviews") return mockReviews as unknown as T
      if (endpoint.startsWith("/reviews/")) {
        const id = endpoint.split("/")[2]
        if (id === mockReviewDetail.id) return mockReviewDetail as unknown as T
        const fallback = mockReviews.find((r: Review) => r.id === id)
        if (fallback) return { ...mockReviewDetail, ...fallback, id: fallback.id } as unknown as T
        return mockReviewDetail as unknown as T
      }
      // Mock mutations
      if (fetchOptions.method === "POST" || fetchOptions.method === "PATCH") {
        return { success: true } as unknown as T
      }
    }

    // Validate runtime API configuration
    appConfig.validateApiConfig()

    const url = `${appConfig.apiUrl}${endpoint}`
    const controller = new AbortController()
    let timedOut = false
    const timeoutId = setTimeout(() => {
      timedOut = true
      controller.abort()
    }, timeoutMs)

    // Honour a caller-supplied signal *in addition to* the timeout. Passing the
    // caller's signal straight through would silently disable the timeout.
    const callerSignal = fetchOptions.signal
    if (callerSignal) {
      if (callerSignal.aborted) {
        controller.abort()
      } else {
        callerSignal.addEventListener("abort", () => controller.abort(), { once: true })
      }
    }

    try {
      const response = await fetch(url, {
        ...fetchOptions,
        signal: controller.signal,
        credentials: "include", // Send session cookie across requests
        headers: {
          "Content-Type": "application/json",
          ...fetchOptions.headers,
        },
      })

      clearTimeout(timeoutId)

      if (!response.ok) {
        let detail: string | undefined
        try {
          const errData = await response.json()
          if (typeof errData?.detail === "string") {
            detail = errData.detail
          } else if (typeof errData?.message === "string") {
            detail = errData.message
          }
        } catch {
          // Response body was not JSON
        }

        const apiError = new ApiError({
          message: detail || `Request failed with status ${response.status}`,
          status: response.status,
          statusText: response.statusText,
          detail,
        })

        // Notify session observers on 401
        if (apiError.isAuthError) {
          this.notifyUnauthorized()
        }

        throw apiError
      }

      // 204 No Content
      if (response.status === 204) {
        return {} as T
      }

      try {
        return (await response.json()) as T
      } catch (jsonErr) {
        throw new ApiError({
          message: "Failed to parse server JSON response.",
          status: response.status,
          statusText: response.statusText,
          detail: jsonErr instanceof Error ? jsonErr.message : "Malformed JSON",
        })
      }
    } catch (error: unknown) {
      clearTimeout(timeoutId)

      if (error instanceof ApiError) {
        throw error
      }

      const isAbort = error instanceof DOMException && error.name === "AbortError"

      // An abort is only a timeout if our own timer fired; otherwise the caller
      // cancelled (component unmount, query invalidation) and should not be
      // surfaced as a network failure.
      if (isAbort && !timedOut) {
        throw new ApiError({
          message: "Request was cancelled.",
          code: "CANCELLED",
        })
      }

      throw new ApiError({
        message: isAbort
          ? `Request timed out after ${timeoutMs / 1000}s.`
          : error instanceof Error
          ? error.message
          : "Network request failed.",
        isNetworkError: true,
        code: isAbort ? "TIMEOUT" : "NETWORK_ERROR",
      })
    }
  }

  // --- Auth ---
  async getAuthMe(): Promise<AuthUser> {
    return this.request<AuthUser>("/auth/me")
  }

  async logout(): Promise<{ status: string }> {
    return this.request<{ status: string }>("/auth/logout", { method: "POST" })
  }

  // --- Repositories ---
  async getRepositories(): Promise<Repository[]> {
    return this.request<Repository[]>("/repos")
  }

  async getRepoSettings(repoId: string): Promise<RepositorySettings> {
    return this.request<RepositorySettings>(`/repos/${repoId}/settings`)
  }

  async updateRepoSettings(
    repoId: string,
    settings: Partial<RepositorySettings>
  ): Promise<RepositorySettings> {
    return this.request<RepositorySettings>(`/repos/${repoId}/settings`, {
      method: "PATCH",
      body: JSON.stringify(settings),
    })
  }

  // --- Dashboard & Ledger ---
  async getDashboardStats(): Promise<DashboardStats> {
    return this.request<DashboardStats>("/stats")
  }

  async getLedgerStats(repoFullName: string): Promise<LedgerStats> {
    return this.request<LedgerStats>(`/ledger/${repoFullName}`)
  }

  async getLedgerTrend(repoFullName: string): Promise<LedgerTrend[]> {
    return this.request<LedgerTrend[]>(`/ledger/${repoFullName}/trend`)
  }

  // --- Reviews ---
  async getReviews(repo?: string, status?: string, severity?: string): Promise<Review[]> {
    const params = new URLSearchParams()
    if (repo) params.set("repo", repo)
    if (status) params.set("status", status)
    if (severity) params.set("severity", severity)
    const queryString = params.toString()
    return this.request<Review[]>(queryString ? `/reviews?${queryString}` : "/reviews")
  }

  async getRepoReviews(repoFullName: string): Promise<Review[]> {
    return this.request<Review[]>(`/repos/${repoFullName}/reviews`)
  }

  async getReview(reviewId: string): Promise<ReviewDetail> {
    return this.request<ReviewDetail>(`/reviews/${reviewId}`)
  }

  // --- HITL ---
  async getHitlPending(): Promise<HitlItem[]> {
    return this.request<HitlItem[]>("/hitl/pending")
  }

  async approveHitl(reviewId: string): Promise<{ success: boolean; github_comment_url?: string }> {
    return this.request<{ success: boolean; github_comment_url?: string }>(
      `/hitl/${reviewId}/approve`,
      { method: "POST" }
    )
  }

  async rejectHitl(reviewId: string): Promise<{ success: boolean }> {
    return this.request<{ success: boolean }>(`/hitl/${reviewId}/reject`, { method: "POST" })
  }
}

export const apiClient = new ApiClient()
