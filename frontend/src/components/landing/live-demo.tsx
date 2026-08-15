"use client"

import { useState, useRef } from "react"
import { motion, AnimatePresence } from "framer-motion"
import { GitPullRequest, Search, Code2, Brain, ShieldAlert, CheckCircle2, ChevronRight, Activity, TerminalSquare } from "lucide-react"

type StepStatus = "pending" | "running" | "completed" | "failed"

interface DemoStep {
  id: string
  label: string
  icon: React.ElementType
  durationMs: number
  status: StepStatus
  parallel?: boolean
}

const initialSteps: DemoStep[] = [
  { id: "pr", label: "Pull Request Detected: feat/payment-gateway (#142)", icon: GitPullRequest, durationMs: 1500, status: "pending" },
  { id: "context", label: "Agent 1: Extracting Repository Context & Call Graphs", icon: Search, durationMs: 2500, status: "pending" },
  { id: "agent2a", label: "Agent 2A: Validating Architecture & SOLID Patterns", icon: Code2, durationMs: 4000, status: "pending", parallel: true },
  { id: "agent2b", label: "Agent 2B: Tracing Logic execution for Race Conditions", icon: Brain, durationMs: 4500, status: "pending", parallel: true },
  { id: "agent2c", label: "Agent 2C: Auditing for OWASP Vulnerabilities", icon: ShieldAlert, durationMs: 3800, status: "pending", parallel: true },
  { id: "critic", label: "Critic Agent: Synthesizing Findings & Removing Duplicates", icon: Activity, durationMs: 2000, status: "pending" },
  { id: "acs", label: "Calculating Architecture Compliance Score (ACS)", icon: TerminalSquare, durationMs: 1500, status: "pending" },
  { id: "done", label: "Review Completed. Publishing to GitHub.", icon: CheckCircle2, durationMs: 500, status: "pending" }
]

export function LiveDemo() {
  const [steps, setSteps] = useState<DemoStep[]>(initialSteps)
  const [isPlaying, setIsPlaying] = useState(false)
  const containerRef = useRef<HTMLDivElement>(null)

  const runDemo = async () => {
    if (isPlaying) return
    setIsPlaying(true)
    
    // Reset
    setSteps(initialSteps.map(s => ({ ...s, status: "pending" })))

    const updateStatus = (id: string, status: StepStatus) => {
      setSteps(prev => prev.map(s => s.id === id ? { ...s, status } : s))
    }

    const sleep = (ms: number) => new Promise(resolve => setTimeout(resolve, ms))

    // Step 1: PR
    updateStatus("pr", "running")
    await sleep(initialSteps[0].durationMs)
    updateStatus("pr", "completed")

    // Step 2: Context
    updateStatus("context", "running")
    await sleep(initialSteps[1].durationMs)
    updateStatus("context", "completed")

    // Step 3: Parallel Agents
    updateStatus("agent2a", "running")
    updateStatus("agent2b", "running")
    updateStatus("agent2c", "running")

    await Promise.all([
      sleep(initialSteps[2].durationMs).then(() => updateStatus("agent2a", "completed")),
      sleep(initialSteps[3].durationMs).then(() => updateStatus("agent2b", "completed")),
      sleep(initialSteps[4].durationMs).then(() => updateStatus("agent2c", "completed"))
    ])

    // Step 4: Critic
    updateStatus("critic", "running")
    await sleep(initialSteps[5].durationMs)
    updateStatus("critic", "completed")

    // Step 5: ACS
    updateStatus("acs", "running")
    await sleep(initialSteps[6].durationMs)
    updateStatus("acs", "completed")

    // Step 6: Done
    updateStatus("done", "running")
    await sleep(initialSteps[7].durationMs)
    updateStatus("done", "completed")

    setTimeout(() => setIsPlaying(false), 3000)
  }

  return (
    <section id="demo" className="py-24 relative z-10 bg-secondary/20 border-y border-border/50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex flex-col lg:flex-row gap-12 items-center">
          
          <div className="lg:w-1/3">
            <motion.h2 
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              className="text-3xl md:text-4xl font-bold tracking-tight text-foreground mb-4"
            >
              Watch the AI Think.
            </motion.h2>
            <motion.p 
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: 0.1 }}
              className="text-lg text-muted-foreground mb-8"
            >
              Experience the multi-agent workflow in real-time. Every review is executed transparently, showing you exactly which agent is running and what it&apos;s looking for.
            </motion.p>
            <motion.button
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: 0.2 }}
              onClick={runDemo}
              disabled={isPlaying}
              className="flex items-center gap-2 px-6 py-3 bg-foreground text-background font-semibold rounded-full hover:bg-foreground/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isPlaying ? (
                <>
                  <span className="h-4 w-4 border-2 border-background/30 border-t-background rounded-full animate-spin" />
                  Reviewing PR...
                </>
              ) : (
                <>
                  <ChevronRight className="w-5 h-5" />
                  Trigger Live Simulation
                </>
              )}
            </motion.button>
          </div>

          <div className="lg:w-2/3 w-full">
            <div className="bg-[#0D1117] border border-border rounded-xl shadow-2xl overflow-hidden font-mono text-sm">
              {/* Terminal Header */}
              <div className="flex items-center gap-2 px-4 py-3 bg-[#161B22] border-b border-border">
                <div className="flex gap-1.5">
                  <div className="w-3 h-3 rounded-full bg-critical" />
                  <div className="w-3 h-3 rounded-full bg-warning" />
                  <div className="w-3 h-3 rounded-full bg-success" />
                </div>
                <div className="mx-auto flex items-center gap-2 text-muted-foreground text-xs">
                  <TerminalSquare className="w-3.5 h-3.5" />
                  ignition-agent-runtime
                </div>
              </div>

              {/* Terminal Body */}
              <div 
                ref={containerRef}
                className="p-6 h-[450px] overflow-y-auto space-y-4"
              >
                {!isPlaying && steps.every(s => s.status === "pending") && (
                  <div className="text-muted-foreground flex items-center h-full justify-center opacity-50">
                    Waiting for Webhook payload...
                  </div>
                )}
                
                <AnimatePresence>
                  {steps.map((step) => {
                    if (step.status === "pending") return null
                    return (
                      <motion.div
                        key={step.id}
                        initial={{ opacity: 0, x: -10 }}
                        animate={{ opacity: 1, x: 0 }}
                        className={`flex items-start gap-4 ${step.parallel ? 'ml-8 border-l-2 border-border pl-4' : ''}`}
                      >
                        <div className="mt-0.5">
                          {step.status === "running" ? (
                            <span className="flex h-5 w-5 items-center justify-center rounded-full bg-primary/20">
                              <span className="h-3 w-3 border-2 border-primary border-t-transparent rounded-full animate-spin" />
                            </span>
                          ) : step.status === "completed" ? (
                            <CheckCircle2 className="h-5 w-5 text-success" />
                          ) : (
                            <step.icon className="h-5 w-5 text-muted-foreground" />
                          )}
                        </div>
                        <div className="flex-1">
                          <p className={`font-medium ${step.status === "running" ? "text-primary animate-pulse" : step.status === "completed" ? "text-foreground" : "text-muted-foreground"}`}>
                            {step.label}
                          </p>
                          {step.status === "completed" && (
                            <p className="text-xs text-muted-foreground mt-1">Completed in {(step.durationMs / 1000).toFixed(1)}s</p>
                          )}
                        </div>
                      </motion.div>
                    )
                  })}
                </AnimatePresence>
                
                {isPlaying && (
                  <motion.div 
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    className="flex items-center gap-2 text-muted-foreground ml-2 mt-4"
                  >
                    <span className="w-2 h-4 bg-primary animate-pulse" />
                  </motion.div>
                )}
              </div>
            </div>
          </div>

        </div>
      </div>
    </section>
  )
}
