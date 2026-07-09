"use client"

import { useReviewStream } from "@/hooks/use-review-stream"
import { ReviewDetail } from "@/lib/types"
import { AgentTimeline } from "./agent-timeline"
import { FindingCard } from "./finding-card"

export function LiveReviewStream({ initialData }: { initialData: ReviewDetail }) {
  const { agents, findings, connectionState, error } = useReviewStream(initialData.id, initialData)

  // Group findings by agent
  const groupedFindings = findings.reduce((acc, finding) => {
    if (!acc[finding.agentId]) acc[finding.agentId] = []
    acc[finding.agentId].push(finding)
    return acc
  }, {} as Record<string, typeof findings>)

  return (
    <div className="space-y-12">
      {/* Connection Indicator */}
      {connectionState === "open" && (
        <div className="flex items-center gap-2 text-xs font-medium text-primary bg-primary/10 w-fit px-3 py-1 rounded-full border border-primary/20">
          <span className="relative flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-primary opacity-75"></span>
            <span className="relative inline-flex rounded-full h-2 w-2 bg-primary"></span>
          </span>
          Live SSE Stream Active
        </div>
      )}
      {connectionState === "connecting" && (
        <div className="flex items-center gap-2 text-xs font-medium text-warning bg-warning/10 w-fit px-3 py-1 rounded-full border border-warning/20">
          <span className="h-3 w-3 rounded-full border-2 border-warning border-t-transparent animate-spin" />
          Connecting to Stream...
        </div>
      )}
      {connectionState === "error" && (
        <div className="flex items-center gap-2 text-xs font-medium text-critical bg-critical/10 w-fit px-3 py-1 rounded-full border border-critical/20">
          <span className="h-2 w-2 rounded-full bg-critical" />
          {error?.message || "Connection Error"}
        </div>
      )}

      {/* Agent Timeline */}
      <section>
        <h2 className="text-lg font-semibold text-foreground mb-6">Agent Progress</h2>
        <AgentTimeline agents={agents} />
      </section>

      {/* Findings */}
      {findings.length > 0 && (
        <section>
          <h2 className="text-lg font-semibold text-foreground mb-6">Detected Findings</h2>
          <div className="space-y-8">
            {Object.entries(groupedFindings).map(([agentId, agentFindings]) => {
              const agentName = agents.find(a => a.id === agentId)?.name || agentId
              return (
                <div key={agentId} className="space-y-4">
                  <h3 className="text-sm font-medium text-muted-foreground uppercase tracking-wider">{agentName}</h3>
                  <div className="space-y-3">
                    {agentFindings.map(finding => (
                      <FindingCard key={finding.id} finding={finding} />
                    ))}
                  </div>
                </div>
              )
            })}
          </div>
        </section>
      )}
    </div>
  )
}
