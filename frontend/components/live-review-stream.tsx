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
    <div className="space-y-10">
      {/* Connection Indicator */}
      <div className="flex items-center gap-2">
        {connectionState === "open" && (
          <div className="flex items-center gap-2 text-xs font-semibold text-[#E85D2F] bg-[#E85D2F]/10 w-fit px-3 py-1.5 rounded-lg border border-[#E85D2F]/30 font-mono shadow-[0_0_12px_rgba(232,93,47,0.1)]">
            <span className="relative flex h-2.5 w-2.5">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-[#E85D2F] opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-[#E85D2F]"></span>
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
        {connectionState === "error" && (
          <div className="flex items-center gap-2 text-xs font-semibold text-critical bg-critical/10 w-fit px-3 py-1.5 rounded-lg border border-critical/35 font-mono">
            <span className="h-2.5 w-2.5 rounded-full bg-critical" />
            {error?.message || "DISCONNECTED"}
          </div>
        )}
      </div>

      {/* Agent Progress */}
      <section className="bg-[#14171A] p-6 rounded-xl border border-[#22262B] shadow-lg shadow-black/25">
        <h2 className="text-sm font-bold text-foreground uppercase tracking-wider mb-6 border-b border-[#22262B] pb-3">Agent Progress Timeline</h2>
        <AgentTimeline agents={agents} />
      </section>

      {/* Findings */}
      {findings.length > 0 && (
        <section className="space-y-6">
          <h2 className="text-sm font-bold text-foreground uppercase tracking-wider border-b border-[#22262B] pb-3">Detected Findings</h2>
          <div className="space-y-8">
            {Object.entries(groupedFindings).map(([agentId, agentFindings]) => {
              const agentName = agents.find(a => a.id === agentId)?.name || agentId
              return (
                <div key={agentId} className="space-y-4">
                  <h3 className="text-xs font-bold text-muted-foreground uppercase tracking-wider font-mono bg-[#14171A] w-fit px-2.5 py-1 rounded border border-[#22262B]">
                    {agentName}
                  </h3>
                  <div className="space-y-3 pl-2 border-l border-[#22262B]">
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
