"use client"

import { useState } from "react"
import { motion, AnimatePresence } from "framer-motion"
import { GitPullRequest, Search, GitFork, ShieldAlert, UserCheck, MessageSquarePlus, LucideIcon } from "lucide-react"

interface PipelineStage {
  id: string
  label: string
  shortDesc: string
  details: string
  icon: LucideIcon
  type: "input" | "process" | "parallel" | "critic" | "output"
}

const STAGES: PipelineStage[] = [
  {
    id: "pr",
    label: "pull request created",
    shortDesc: "Trigger point",
    details: "GitHub webhook triggers the Ignition analysis flow on commits, branch updates, or new pull requests.",
    icon: GitPullRequest,
    type: "input"
  },
  {
    id: "context",
    label: "context fetcher",
    shortDesc: "AST & imports mapping",
    details: "Fetches full repository context, structures syntax trees (ASTs), and maps dependency imports.",
    icon: Search,
    type: "process"
  },
  {
    id: "fork",
    label: "parallel fork",
    shortDesc: "Task fan-out",
    details: "Distributes task payloads to specialized static, logic, and security agent node environments.",
    icon: GitFork,
    type: "process"
  },
  {
    id: "specialists",
    label: "specialist agents",
    shortDesc: "Parallel logic analysis",
    details: "Parallel nodes evaluate the changes: Structural Inspector (patterns), Chaos & Logic Assessor (race conditions/leaks), and Security Auditor (vulnerabilities).",
    icon: ShieldAlert,
    type: "parallel"
  },
  {
    id: "critic",
    label: "critic & synthesizer",
    shortDesc: "False-positive pruning",
    details: "Deduplicates issues, runs secondary validation passes, and computes final quality metrics.",
    icon: UserCheck,
    type: "critic"
  },
  {
    id: "post",
    label: "publish review",
    shortDesc: "GitHub feedback loop",
    details: "Posts precise inline comments directly back to the pull request thread on GitHub.",
    icon: MessageSquarePlus,
    type: "output"
  }
]

export function PipelineDiagram() {
  const [activeStage, setActiveStage] = useState<string | null>("pr")

  return (
    <div className="w-full bg-card/30 border border-border/80 rounded-2xl p-6 sm:p-8 backdrop-blur-md relative overflow-hidden">
      <div className="absolute inset-0 bg-gradient-to-br from-primary/5 via-transparent to-transparent pointer-events-none" />
      
      <div className="flex flex-col gap-8">
        {/* Connection pipeline representation */}
        <div className="flex flex-wrap lg:flex-nowrap justify-between items-center gap-4 relative">
          {/* Connecting line */}
          <div className="hidden lg:block absolute left-8 right-8 top-1/2 h-[2px] bg-gradient-to-r from-primary/20 via-primary/50 to-primary/20 -translate-y-1/2 -z-10" />

          {STAGES.map((stage, idx) => {
            const Icon = stage.icon
            const isActive = activeStage === stage.id

            return (
              <div 
                key={stage.id} 
                className="flex-1 min-w-[130px] flex flex-col items-center"
                onMouseEnter={() => setActiveStage(stage.id)}
                onClick={() => setActiveStage(stage.id)}
              >
                <div 
                  className={`h-16 w-16 rounded-full flex items-center justify-center cursor-pointer transition-all duration-300 border relative ${
                    isActive 
                      ? "bg-primary text-primary-foreground border-primary shadow-[0_0_25px_rgba(255,69,0,0.5)] scale-110" 
                      : "bg-background text-muted-foreground border-border hover:border-primary/50 hover:text-foreground"
                  }`}
                >
                  <Icon className="h-6 w-6" />
                  
                  {/* Small step index number */}
                  <span className="absolute -top-1 -right-1 text-[10px] px-1.5 py-0.5 rounded-full bg-secondary border border-border text-foreground font-mono">
                    {idx + 1}
                  </span>
                </div>
                
                <span className="mt-3 text-xs font-semibold tracking-tight text-center max-w-[100px] text-foreground lowercase">
                  {stage.label}
                </span>
              </div>
            )
          })}
        </div>

        {/* Dynamic Detail Card */}
        <div className="min-h-[140px] bg-background/50 border border-border/60 rounded-xl p-6 transition-all duration-300">
          <AnimatePresence mode="wait">
            {activeStage && (
              <motion.div
                key={activeStage}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                transition={{ duration: 0.2 }}
                className="flex flex-col gap-2"
              >
                <div className="flex items-center gap-2">
                  <span className="text-xs uppercase font-mono font-bold tracking-widest text-primary">
                    {STAGES.find(s => s.id === activeStage)?.shortDesc}
                  </span>
                </div>
                <h3 className="text-lg font-bold text-foreground lowercase">
                  {STAGES.find(s => s.id === activeStage)?.label}
                </h3>
                <p className="text-sm sm:text-base text-muted-foreground leading-relaxed">
                  {STAGES.find(s => s.id === activeStage)?.details}
                </p>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>
    </div>
  )
}
