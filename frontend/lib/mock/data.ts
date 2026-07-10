import { DashboardStats, Repository, Review } from "../types"

export const mockStats: DashboardStats = {
  activeReviews: 12,
  hitlPending: 3,
  avgAcsScore: 84,
  issuesFound: 156,
}

export const mockRepositories: Repository[] = [
  {
    id: "repo-1",
    name: "core-banking-api",
    owner: "financial-systems",
    lastReviewDate: new Date().toISOString(),
    acsScore: 92,
    status: "healthy",
    language: "Go",
  },
  {
    id: "repo-2",
    name: "customer-portal-web",
    owner: "frontend-platform",
    lastReviewDate: new Date(Date.now() - 86400000).toISOString(),
    acsScore: 78,
    status: "warning",
    language: "TypeScript",
  },
  {
    id: "repo-3",
    name: "auth-service",
    owner: "security",
    lastReviewDate: new Date(Date.now() - 172800000).toISOString(),
    acsScore: 54,
    status: "critical",
    language: "Rust",
  },
  {
    id: "repo-4",
    name: "data-pipeline-workers",
    owner: "data-eng",
    lastReviewDate: new Date(Date.now() - 3600000).toISOString(),
    acsScore: 88,
    status: "healthy",
    language: "Python",
  },
]

export const mockReviews: Review[] = [
  {
    id: "rev-101",
    repoId: "repo-1",
    repoName: "core-banking-api",
    pullRequestNumber: 432,
    title: "feat: Implement SEPA transfers",
    status: "running",
    severity: "low",
    findingsCount: 0,
    createdAt: new Date().toISOString(),
  },
  {
    id: "rev-102",
    repoId: "repo-2",
    repoName: "customer-portal-web",
    pullRequestNumber: 89,
    title: "fix: Dashboard rendering infinite loop",
    status: "completed",
    severity: "high",
    findingsCount: 4,
    createdAt: new Date(Date.now() - 7200000).toISOString(),
  },
  {
    id: "rev-103",
    repoId: "repo-3",
    repoName: "auth-service",
    pullRequestNumber: 210,
    title: "chore: Update JWT signing keys algorithm",
    status: "completed",
    severity: "critical",
    findingsCount: 1,
    createdAt: new Date(Date.now() - 14400000).toISOString(),
  },
  {
    id: "rev-104",
    repoId: "repo-4",
    repoName: "data-pipeline-workers",
    pullRequestNumber: 56,
    title: "feat: Add Kafka consumer for telemetry",
    status: "queued",
    severity: "medium",
    findingsCount: 2,
    createdAt: new Date(Date.now() - 28800000).toISOString(),
  },
]
