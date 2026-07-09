export type SeverityLevel = "info" | "warning" | "danger" | "critical" | "success" | "none" | "low" | "medium" | "high"
export type ReviewStatusType = "queued" | "running" | "paused" | "waiting_hitl" | "completed" | "failed" | "cancelled"

export interface Repository {
  id: string
  name: string
  owner: string
  lastReviewDate: string
  acsScore: number
  status: "healthy" | "warning" | "critical"
  language: string
}

export interface Review {
  id: string
  repoId: string
  repoName: string
  pullRequestNumber: number
  title: string
  status: ReviewStatusType
  severity: SeverityLevel
  findingsCount: number
  createdAt: string
  completedAt?: string
  duration?: string
  acsScore?: number
}

export interface DashboardStats {
  activeReviews: number
  hitlPending: number
  avgAcsScore: number
  issuesFound: number
}

export interface ReviewDiff {
  file: string
  additions: number
  deletions: number
  content: string // Contains unified diff format
}

export interface Finding {
  id: string
  agentId: string
  severity: SeverityLevel
  file: string
  line?: number
  description: string
  rule: string
  recommendation: string
  suggestedFix?: string
}

export interface AgentProgress {
  id: string
  name: string
  status: "pending" | "running" | "completed" | "failed"
  executionTimeMs?: number
  findingCount: number
}

export interface RegressionAlert {
  isRegression: boolean
  ruleRegressed?: string
  previousScore?: number
  currentScore?: number
  impact?: string
  recommendation?: string
}

export interface ReviewDetail extends Review {
  author: string
  branch: string
  commitSha: string
  filesChanged: number
  linesAdded: number
  linesDeleted: number
  previousAcsScore: number
  regression: RegressionAlert
  agents: AgentProgress[]
  findings: Finding[]
  diffs: ReviewDiff[]
  githubCommentPreview?: string
}

export interface HitlItem extends ReviewDetail {
  waitingSince: string
}

export interface RepositorySettings {
  enableAiReview: boolean
  enableAutoFix: boolean
  enableHitl: boolean
  securityScan: boolean
  architectureScan: boolean
  logicScan: boolean
}

export interface LedgerStats {
  averageAcs: number
  totalReviews: number
  criticalFindings: number
  activeRegressions: number
}

export interface LedgerTrend {
  date: string
  acsScore: number
  reviewsCount: number
  criticalCount: number
}

export type SseEventType = 
  | "review.started"
  | "agent.started"
  | "agent.completed"
  | "agent.failed"
  | "critic.started"
  | "critic.completed"
  | "acs.updated"
  | "regression.detected"
  | "waiting.hitl"
  | "hitl.approved"
  | "hitl.rejected"
  | "review.completed"
  | "review.failed"

export interface SseEventPayload {
  type: SseEventType
  reviewId: string
  agentId?: string
  executionTimeMs?: number
  findingCount?: number
  acsScore?: number
  status?: string
}

