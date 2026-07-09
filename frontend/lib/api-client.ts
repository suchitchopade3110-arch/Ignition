import { DashboardStats, Repository, Review, ReviewDetail, HitlItem, RepositorySettings, LedgerStats, LedgerTrend } from "./types"
import { mockRepositories } from "./mock/data"
import { mockStats } from "./mock/data"
import { mockReviewList } from "./mock/reviews"
import { mockReviewDetail } from "./mock/review-detail"

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api"

/**
 * Enterprise API Client using native fetch.
 * Implements robust error handling and types.
 */
class ApiClient {
  private async request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const url = `${API_BASE_URL}${endpoint}`
    
    // Fallback to mock data for Phase 3 demo purposes if no real backend
    if (!process.env.NEXT_PUBLIC_API_URL) {
      if (typeof window !== "undefined") {
        await new Promise(resolve => setTimeout(resolve, 500)) // Simulate network latency
      }
      
      if (endpoint === "/auth/me") return { id: "user-1", name: "Demo User" } as unknown as T
      if (endpoint === "/stats") return mockStats as unknown as T
      if (endpoint === "/repos") return mockRepositories as unknown as T
      if (endpoint === "/reviews") return mockReviewList as unknown as T
      if (endpoint === "/hitl/pending") {
        const pending = mockReviewList.filter(r => r.status === "waiting_hitl")
        return pending.map(p => ({ ...mockReviewDetail, ...p, waitingSince: p.createdAt })) as unknown as T
      }
      if (endpoint.startsWith("/repos/") && endpoint.endsWith("/settings")) {
        return {
          enableAiReview: true,
          enableAutoFix: false,
          enableHitl: true,
          securityScan: true,
          architectureScan: true,
          logicScan: true
        } as unknown as T
      }
      if (endpoint.startsWith("/ledger/") && !endpoint.endsWith("/trend")) {
        return {
          averageAcs: 87,
          totalReviews: 124,
          criticalFindings: 3,
          activeRegressions: 1
        } as unknown as T
      }
      if (endpoint.startsWith("/ledger/") && endpoint.endsWith("/trend")) {
        return [
          { date: "2026-01", acsScore: 78, reviewsCount: 45, criticalCount: 12 },
          { date: "2026-02", acsScore: 82, reviewsCount: 52, criticalCount: 8 },
          { date: "2026-03", acsScore: 81, reviewsCount: 48, criticalCount: 9 },
          { date: "2026-04", acsScore: 86, reviewsCount: 61, criticalCount: 4 },
          { date: "2026-05", acsScore: 89, reviewsCount: 59, criticalCount: 2 },
          { date: "2026-06", acsScore: 87, reviewsCount: 65, criticalCount: 3 },
          { date: "2026-07", acsScore: 92, reviewsCount: 24, criticalCount: 1 },
        ] as unknown as T
      }
      if (endpoint.startsWith("/reviews/")) {
        const id = endpoint.split("/")[2]
        if (id === mockReviewDetail.id) return mockReviewDetail as unknown as T
        const fallback = mockReviewList.find(r => r.id === id)
        if (fallback) return { ...mockReviewDetail, ...fallback, id: fallback.id } as unknown as T
        return mockReviewDetail as unknown as T
      }
      // Mock mutations
      if (options.method === "POST" || options.method === "PATCH") {
        return { success: true } as unknown as T
      }
    }

    try {
      const response = await fetch(url, {
        ...options,
        headers: {
          "Content-Type": "application/json",
          ...options.headers,
        },
      })

      if (!response.ok) {
        // Detailed error for Toasts
        let message = `API Error: ${response.status}`
        try {
          const errData = await response.json()
          if (errData.detail) message = errData.detail
        } catch {
          message = response.statusText || message
        }
        throw new Error(message)
      }

      // Handle 204 No Content
      if (response.status === 204) {
        return {} as T
      }

      return response.json()
    } catch (error) {
      console.error(`Fetch failed for ${endpoint}:`, error)
      throw error
    }
  }

  // --- Auth ---
  async getAuthMe() { return this.request("/auth/me") }
  async logout() { return this.request("/auth/logout", { method: "POST" }) }

  // --- Repositories ---
  async getRepositories(): Promise<Repository[]> { return this.request<Repository[]>("/repos") }
  async getRepoSettings(repoId: string): Promise<RepositorySettings> { return this.request<RepositorySettings>(`/repos/${repoId}/settings`) }
  async updateRepoSettings(repoId: string, settings: Partial<RepositorySettings>) { return this.request(`/repos/${repoId}/settings`, { method: "PATCH", body: JSON.stringify(settings) }) }

  // --- Dashboard & Ledger ---
  async getDashboardStats(): Promise<DashboardStats> { return this.request<DashboardStats>("/stats") }
  async getLedgerStats(repoFullName: string): Promise<LedgerStats> { return this.request<LedgerStats>(`/ledger/${repoFullName}`) }
  async getLedgerTrend(repoFullName: string): Promise<LedgerTrend[]> { return this.request<LedgerTrend[]>(`/ledger/${repoFullName}/trend`) }

  // --- Reviews ---
  async getReviews(): Promise<Review[]> { return this.request<Review[]>("/reviews") }
  async getRepoReviews(repoFullName: string): Promise<Review[]> { return this.request<Review[]>(`/repos/${repoFullName}/reviews`) }
  async getReview(id: string): Promise<ReviewDetail> { return this.request<ReviewDetail>(`/reviews/${id}`) }

  // --- HITL ---
  async getHitlPending(): Promise<HitlItem[]> { return this.request<HitlItem[]>("/hitl/pending") }
  async approveHitl(reviewId: string) { return this.request(`/hitl/${reviewId}/approve`, { method: "POST" }) }
  async rejectHitl(reviewId: string) { return this.request(`/hitl/${reviewId}/reject`, { method: "POST" }) }
}

export const apiClient = new ApiClient()
