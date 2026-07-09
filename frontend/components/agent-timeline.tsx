"use client"

import { motion } from "framer-motion"
import { CheckCircle2, Clock, Loader2, XCircle } from "lucide-react"
import { AgentProgress } from "@/lib/types"
import { cn } from "@/lib/utils"

interface AgentTimelineProps {
  agents: AgentProgress[]
}

const statusConfig = {
  pending: { icon: Clock, className: "text-muted-foreground", bg: "bg-secondary" },
  running: { icon: Loader2, className: "text-primary animate-spin", bg: "bg-primary/20" },
  completed: { icon: CheckCircle2, className: "text-success", bg: "bg-success/20" },
  failed: { icon: XCircle, className: "text-critical", bg: "bg-critical/20" },
}

function AgentNode({ agent, isParallel = false }: { agent: AgentProgress; isParallel?: boolean }) {
  const { icon: Icon, className, bg } = statusConfig[agent.status]

  return (
    <div className={cn("flex items-center gap-4 p-4 rounded-xl border border-border bg-card relative z-10", isParallel && "flex-1")}>
      <div className={cn("flex-shrink-0 flex items-center justify-center h-10 w-10 rounded-full", bg)}>
        <Icon className={cn("h-5 w-5", className)} />
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-foreground truncate">{agent.name}</p>
        <div className="flex items-center gap-2 mt-1">
          <span className="text-xs text-muted-foreground">
            {agent.status === "completed" || agent.status === "failed" 
              ? `${(agent.executionTimeMs || 0) / 1000}s` 
              : agent.status === "running" ? "Running..." : "Waiting"}
          </span>
          {agent.findingCount > 0 && (
            <>
              <span className="text-muted-foreground text-xs">•</span>
              <span className="text-xs font-medium text-warning">{agent.findingCount} finding{agent.findingCount !== 1 ? 's' : ''}</span>
            </>
          )}
        </div>
      </div>
    </div>
  )
}

export function AgentTimeline({ agents }: AgentTimelineProps) {
  if (!agents || agents.length === 0) return null

  // Hardcode the LangGraph structure mapping for this specific demo
  // Linear: Context Fetcher (0) -> Rule Gate (1)
  // Parallel: 2A (2), 2B (3), 2C (4)
  // Linear: Critic (5) -> Auto Fix (6) -> GitHub (faked, not in list)
  
  const linearStart = agents.slice(0, 2)
  const parallelMiddle = agents.slice(2, 5)
  const linearEnd = agents.slice(5)

  return (
    <div className="relative py-4">
      <div className="absolute top-0 bottom-0 left-[3rem] w-0.5 bg-border -z-0" />
      
      <div className="space-y-8 relative z-10">
        {/* Start Nodes */}
        {linearStart.map((agent, i) => (
          <motion.div 
            key={agent.id}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.1 }}
          >
            <AgentNode agent={agent} />
          </motion.div>
        ))}

        {/* Parallel Nodes Container */}
        {parallelMiddle.length > 0 && (
          <motion.div 
            className="flex flex-col md:flex-row gap-4 ml-12 md:ml-0 relative"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3 }}
          >
            {/* Desktop branch lines */}
            <div className="hidden md:block absolute -top-8 left-[3rem] right-[3rem] h-8 border-t-2 border-l-2 border-r-2 border-border rounded-t-xl" />
            
            {parallelMiddle.map((agent) => (
              <AgentNode key={agent.id} agent={agent} isParallel />
            ))}

            {/* Desktop converge lines */}
            <div className="hidden md:block absolute -bottom-8 left-[3rem] right-[3rem] h-8 border-b-2 border-l-2 border-r-2 border-border rounded-b-xl" />
          </motion.div>
        )}

        {/* End Nodes */}
        {linearEnd.map((agent, i) => (
          <motion.div 
            key={agent.id}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.5 + (i * 0.1) }}
          >
            <AgentNode agent={agent} />
          </motion.div>
        ))}
      </div>
    </div>
  )
}
