import {
  DashboardStats,
  HitlItem,
  LedgerStats,
  LedgerTrend,
  Repository,
  RepositorySettings,
  Review,
  ReviewDetail,
} from "@/types"

export const mockStats: DashboardStats = {
  activeReviews: 12,
  hitlPending: 3,
  avgAcsScore: 84,
  issuesFound: 156,
  issuesFoundTrend: { value: 8, isPositive: true },
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

export const mockRepoSettings: RepositorySettings = {
  enableAiReview: true,
  enableAutoFix: false,
  enableHitl: true,
  securityScan: true,
  architectureScan: true,
  logicScan: true,
}

export const mockReviewDetail: ReviewDetail = {
  id: "rev-101",
  repoId: "repo-1",
  repoName: "core-banking-api",
  pullRequestNumber: 432,
  title: "feat: Implement SEPA transfers",
  status: "running",
  severity: "low",
  findingsCount: 0,
  createdAt: new Date().toISOString(),
  author: "demo-dev",
  branch: "feature/sepa-v1",
  commitSha: "a9f82d1c7e6b5a4d3c2b1a0f9e8d7c6b5a4d3c2b",
  filesChanged: 3,
  linesAdded: 142,
  linesDeleted: 18,
  previousAcsScore: 88,
  regression: {
    isRegression: false,
  },
  duration: "42s",
  acsScore: 88,
  agents: [
    { id: "agent_1_triage", name: "Triage & Boundary", status: "completed", findingCount: 0, executionTimeMs: 1200 },
    { id: "agent_2a_struct", name: "Structural Analysis", status: "running", findingCount: 0 },
    { id: "agent_2b_chaos", name: "Edge Case & Chaos", status: "pending", findingCount: 0 },
    { id: "agent_2c_security", name: "Security & Secrets", status: "pending", findingCount: 0 },
    { id: "agent_3_critic", name: "Synthesis & Critic", status: "pending", findingCount: 0 },
  ],
  findings: [],
  diffs: [],
  githubCommentPreview: "### AI Code Review Report\nAnalysis in progress...",
}

export const mockHitlPending: HitlItem[] = [
  {
    ...mockReviewDetail,
    id: "rev-103",
    repoId: "repo-3",
    repoName: "auth-service",
    pullRequestNumber: 210,
    title: "chore: Update JWT signing keys algorithm",
    severity: "critical",
    findingsCount: 1,
    acsScore: 54,
    linesAdded: 45,
    linesDeleted: 12,
    waitingSince: new Date(Date.now() - 3600000).toISOString(),
  },
]

export const mockLedgerStats: LedgerStats = {
  averageAcs: 84,
  totalReviews: 48,
  criticalFindings: 6,
  activeRegressions: 1,
}

export const mockLedgerTrend: LedgerTrend[] = [
  { date: "2026-08-01", acsScore: 88, reviewsCount: 4, criticalCount: 0 },
  { date: "2026-08-05", acsScore: 82, reviewsCount: 8, criticalCount: 2 },
  { date: "2026-08-10", acsScore: 85, reviewsCount: 12, criticalCount: 1 },
  { date: "2026-08-15", acsScore: 84, reviewsCount: 15, criticalCount: 1 },
]
