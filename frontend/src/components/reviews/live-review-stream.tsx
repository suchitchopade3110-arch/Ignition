"use client"

import { useReviewStream } from "@/hooks/use-review-stream"
import { ReviewDetail } from "@/types"
import { AgentTimeline } from "./agent-timeline"
import { FindingCard } from "./finding-card"

export function LiveReviewStream({ initialData }: { initialData: ReviewDetail }) {
  const { agents, findings, connectionState, error, liveAnnouncement } = useReviewStream(initialData.id, initialData)

  // Group findings by agent
  const groupedFindings = findings.reduce((acc, finding) => {
    if (!acc[finding.agentId]) acc[finding.agentId] = []
    acc[finding.agentId].push(finding)
    return acc
  }, {} as Record<string, typeof findings>)

  return (
    <div className="space-y-10">
      {/* Screen Reader Live Announcements */}
      <div className="sr-only" aria-live="polite" aria-atomic="true">
        {liveAnnouncement}
      </div>

      {/* Connection Indicator */}
      <div className="flex items-center gap-2">
        {connectionState === "open" && (
          <div className="flex items-center gap-2 text-xs font-semibold text-primary bg-primary/10 w-fit px-3 py-1.5 rounded-lg border border-primary/30 font-mono">
            <span className="relative flex h-2.5 w-2.5">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-primary opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-primary"></span>
            </span>
            STREAMING LIVE UPDATE
          </div>
        )}
        {connectionState === "connecting" && (
          <div className="flex items-center gap-2 text-xs font-semibold text-warning bg-warning/10 w-fit px-3 py-1.5 rounded-lg border border-warning/35 font-mono">
            <span className="h-3.5 w-3.5 rounded-full border-2 border-warning border-t-transparent animate-spin" />
            CONNECTING PIPELINE...
          </div>
        )}
        {connectionState === "reconnecting" && (
          <div className="flex items-center gap-2 text-xs font-semibold text-warning bg-warning/10 w-fit px-3 py-1.5 rounded-lg border border-warning/35 font-mono">
            <span className="h-3.5 w-3.5 rounded-full border-2 border-warning border-t-transparent animate-spin" />
            {error?.message || "RECONNECTING..."}
          </div>
        )}
        {connectionState === "failed" && (
          <div className="flex items-center gap-2 text-xs font-semibold text-critical bg-critical/10 w-fit px-3 py-1.5 rounded-lg border border-critical/35 font-mono">
            <span className="h-2.5 w-2.5 rounded-full bg-critical" />
            {error?.message || "STREAM DISCONNECTED"}
          </div>
        )}
      </div>

      {/* Agent Progress */}
      <section className="bg-card p-4 sm:p-6 rounded-xl border border-border">
        <h2 className="text-sm font-bold text-foreground uppercase tracking-wider mb-6 border-b border-border pb-3">
          Agent Progress Timeline
        </h2>
        <AgentTimeline agents={agents} />
      </section>

      {/* Findings */}
      {findings.length > 0 && (
        <section className="space-y-6">
          <h2 className="text-sm font-bold text-foreground uppercase tracking-wider border-b border-border pb-3">
            Detected Findings
          </h2>
          <div className="space-y-8">
            {Object.entries(groupedFindings).map(([agentId, agentFindings]) => {
              const agentName = agents.find((a) => a.id === agentId)?.name || agentId
              return (
                <div key={agentId} className="space-y-4">
                  <h3 className="text-xs font-bold text-muted-foreground uppercase tracking-wider font-mono bg-secondary/50 w-fit px-2.5 py-1 rounded border border-border">
                    {agentName}
                  </h3>
                  <div className="space-y-3 pl-2 border-l border-border">
                    {agentFindings.map((finding) => (
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
