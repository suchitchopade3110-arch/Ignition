import { ReviewDetail } from "../types"

export const mockReviewDetail: ReviewDetail = {
  id: "rev-101",
  repoId: "repo-1",
  repoName: "core-banking-api",
  pullRequestNumber: 432,
  title: "feat: Implement SEPA transfers",
  status: "running",
  severity: "critical",
  findingsCount: 3,
  createdAt: new Date().toISOString(),
  acsScore: 92,
  author: "jdoe-dev",
  branch: "feature/sepa-transfers",
  commitSha: "a1b2c3d4e5f67890a1b2c3d4e5f67890a1b2c3d4",
  filesChanged: 12,
  linesAdded: 345,
  linesDeleted: 23,
  previousAcsScore: 95,
  regression: {
    isRegression: true,
    ruleRegressed: "No external HTTP calls without circuit breaker",
    previousScore: 95,
    currentScore: 92,
    impact: "High risk of cascading failures during SEPA API downtime.",
    recommendation: "Wrap the external SEPA gateway calls in a CircuitBreaker pattern.",
  },
  agents: [
    {
      id: "agent-1",
      name: "Context Fetcher",
      status: "completed",
      executionTimeMs: 1250,
      findingCount: 0,
    },
    {
      id: "agent-gate",
      name: "Hard Rule Gate",
      status: "completed",
      executionTimeMs: 400,
      findingCount: 0,
    },
    {
      id: "agent-2a",
      name: "Structural Inspector",
      status: "completed",
      executionTimeMs: 4500,
      findingCount: 1,
    },
    {
      id: "agent-2b",
      name: "Chaos & Logic Assessor",
      status: "completed",
      executionTimeMs: 6200,
      findingCount: 2,
    },
    {
      id: "agent-2c",
      name: "Security Auditor",
      status: "running",
      executionTimeMs: 8000,
      findingCount: 0,
    },
    {
      id: "agent-critic",
      name: "Critic & Synthesizer",
      status: "pending",
      findingCount: 0,
    },
    {
      id: "agent-autofix",
      name: "Auto Fix Generator",
      status: "pending",
      findingCount: 0,
    },
  ],
  findings: [
    {
      id: "find-1",
      agentId: "agent-2a",
      severity: "medium",
      file: "src/services/sepa/client.go",
      line: 45,
      description: "Direct HTTP call to external service without circuit breaker.",
      rule: "ARC-004: Resilience patterns for external dependencies",
      recommendation: "Implement a circuit breaker using the standard company library.",
      suggestedFix: "```go\n// Add this wrapper\ncb := circuitbreaker.New(\"sepa-gateway\")\nerr := cb.Execute(func() error {\n  return http.Get(url)\n})\n```",
    },
    {
      id: "find-2",
      agentId: "agent-2b",
      severity: "critical",
      file: "src/db/migrations/20260709_sepa.sql",
      line: 12,
      description: "Adding a non-null column without a default value will lock the table.",
      rule: "DB-012: Zero-downtime migrations",
      recommendation: "Add the column as nullable first, backfill data, then alter to non-null.",
    },
    {
      id: "find-3",
      agentId: "agent-2b",
      severity: "low",
      file: "src/models/transfer.go",
      line: 88,
      description: "Potential race condition in memory cache update.",
      rule: "CONC-002: Safe map access",
      recommendation: "Use a sync.RWMutex or sync.Map for the transfers cache.",
      suggestedFix: "```go\nvar cache sync.Map\ncache.Store(id, transfer)\n```",
    },
  ],
  diffs: [
    {
      file: "src/services/sepa/client.go",
      additions: 45,
      deletions: 2,
      content: `@@ -40,8 +40,51 @@
 func (c *Client) ExecuteTransfer(ctx context.Context, req *TransferRequest) error {
-       // TODO: Implement SEPA
-       return errors.New("not implemented")
+       log.Printf("Starting SEPA transfer for %s", req.ID)
+       
+       payload, err := json.Marshal(req)
+       if err != nil {
+               return fmt.Errorf("failed to marshal request: %w", err)
+       }
+       
+       // FIXME: Direct HTTP call without circuit breaker (Flagged by Agent 2A)
+       resp, err := http.Post(c.baseURL+"/transfers", "application/json", bytes.NewReader(payload))
+       if err != nil {
+               return fmt.Errorf("http request failed: %w", err)
+       }
+       defer resp.Body.Close()
+       
+       if resp.StatusCode >= 400 {
+               return fmt.Errorf("upstream error: %s", resp.Status)
+       }
+       
+       return nil
 }`,
    },
  ],
  githubCommentPreview: `### 🤖 Ignition AI Code Review

⚠️ **Architecture Score dropped from 95 to 92.**

#### 🚨 Critical Findings
* **src/db/migrations/20260709_sepa.sql:12** - Adding a non-null column without a default value will lock the table. (Rule: DB-012)

#### ⚠️ Warnings
* **src/services/sepa/client.go:45** - Direct HTTP call to external service without circuit breaker. (Rule: ARC-004)

---
*Reviewed by Ignition Multi-Agent System*`,
}
