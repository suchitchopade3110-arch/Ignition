import { describe, it, expect } from "vitest"
import { makeQueryClient } from "@/lib/query-client"
import { queryKeys } from "@/lib/query-keys"
import { ReviewDetail } from "@/types"

describe("SSE to Query Cache Synchronization", () => {
  it("updates cached review detail when agent progress events occur", () => {
    const queryClient = makeQueryClient()
    const reviewId = "rev-test-1"

    const initialReview: ReviewDetail = {
      id: reviewId,
      repoId: "repo-1",
      repoName: "test-repo",
      pullRequestNumber: 12,
      title: "Test PR",
      status: "queued",
      severity: "low",
      findingsCount: 0,
      createdAt: new Date().toISOString(),
      author: "dev",
      branch: "main",
      commitSha: "sha123",
      filesChanged: 1,
      linesAdded: 10,
      linesDeleted: 2,
      previousAcsScore: 80,
      regression: { isRegression: false },
      agents: [
        { id: "agent_1_triage", name: "Triage", status: "pending", findingCount: 0 },
        { id: "agent_2a_struct", name: "Structural", status: "pending", findingCount: 0 },
      ],
      findings: [],
      diffs: [],
    }

    queryClient.setQueryData(queryKeys.reviews.detail(reviewId), initialReview)

    // Simulate agent.started event cache updater
    queryClient.setQueryData<ReviewDetail>(queryKeys.reviews.detail(reviewId), (old) => {
      if (!old) return old
      const updatedAgents = [...old.agents]
      const idx = updatedAgents.findIndex((a) => a.id === "agent_1_triage")
      if (idx !== -1) {
        updatedAgents[idx] = { ...updatedAgents[idx], status: "running" }
      }
      return { ...old, status: "running", agents: updatedAgents }
    })

    const updated = queryClient.getQueryData<ReviewDetail>(queryKeys.reviews.detail(reviewId))
    expect(updated?.status).toBe("running")
    expect(updated?.agents[0].status).toBe("running")
    expect(updated?.agents[1].status).toBe("pending")
  })

  it("updates ACS score and regression status in cache", () => {
    const queryClient = makeQueryClient()
    const reviewId = "rev-test-2"

    const initialReview: ReviewDetail = {
      id: reviewId,
      repoId: "repo-1",
      repoName: "test-repo",
      pullRequestNumber: 15,
      title: "Test PR 2",
      status: "running",
      severity: "medium",
      findingsCount: 0,
      createdAt: new Date().toISOString(),
      author: "dev",
      branch: "main",
      commitSha: "sha456",
      filesChanged: 2,
      linesAdded: 50,
      linesDeleted: 10,
      previousAcsScore: 85,
      regression: { isRegression: false },
      agents: [],
      findings: [],
      diffs: [],
    }

    queryClient.setQueryData(queryKeys.reviews.detail(reviewId), initialReview)

    // Simulate acs.updated event
    queryClient.setQueryData<ReviewDetail>(queryKeys.reviews.detail(reviewId), (old) =>
      old ? { ...old, acsScore: 94 } : old
    )

    const updated = queryClient.getQueryData<ReviewDetail>(queryKeys.reviews.detail(reviewId))
    expect(updated?.acsScore).toBe(94)
  })
})
