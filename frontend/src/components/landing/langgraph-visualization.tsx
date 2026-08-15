"use client"

import { motion } from "framer-motion"
import { GitPullRequest, Code2, ShieldAlert, Zap, Network, Brain, CheckCircle2 } from "lucide-react"

export function LangGraphVisualization() {
  const nodes = [
    { id: "pr", label: "GitHub PR", icon: GitPullRequest, x: 50, y: 50, color: "text-foreground" },
    { id: "agent1", label: "Context Fetcher", icon: Network, x: 50, y: 150, color: "text-primary" },
    { id: "gate", label: "Hard Rule Gate", icon: Zap, x: 50, y: 250, color: "text-warning" },
    
    // Parallel Agents
    { id: "agent2a", label: "Structural", icon: Code2, x: 10, y: 350, color: "text-primary" },
    { id: "agent2b", label: "Logic", icon: Brain, x: 50, y: 350, color: "text-primary" },
    { id: "agent2c", label: "Security", icon: ShieldAlert, x: 90, y: 350, color: "text-primary" },
    
    { id: "critic", label: "Critic & Synthesizer", icon: Network, x: 50, y: 450, color: "text-primary" },
    { id: "done", label: "Ready for Merge", icon: CheckCircle2, x: 50, y: 550, color: "text-success" },
  ]

  const paths = [
    { from: "pr", to: "agent1" },
    { from: "agent1", to: "gate" },
    { from: "gate", to: "agent2a" },
    { from: "gate", to: "agent2b" },
    { from: "gate", to: "agent2c" },
    { from: "agent2a", to: "critic" },
    { from: "agent2b", to: "critic" },
    { from: "agent2c", to: "critic" },
    { from: "critic", to: "done" },
  ]

  const getPathData = (from: string, to: string) => {
    const f = nodes.find((n) => n.id === from)
    const t = nodes.find((n) => n.id === to)
    if (!f || !t) return ""
    
    // Create smooth curved lines
    const midY = (f.y + t.y) / 2
    return `M ${f.x} ${f.y} C ${f.x} ${midY}, ${t.x} ${midY}, ${t.x} ${t.y}`
  }

  return (
    <div className="relative w-full aspect-square max-w-[500px] mx-auto select-none pointer-events-none">
      <svg className="absolute inset-0 w-full h-full" viewBox="0 0 100 600" preserveAspectRatio="xMidYMid meet">
        <defs>
          <linearGradient id="flowGradient" x1="0%" y1="0%" x2="0%" y2="100%">
            <stop offset="0%" stopColor="rgba(255, 69, 0, 0)" />
            <stop offset="50%" stopColor="rgba(255, 69, 0, 0.8)" />
            <stop offset="100%" stopColor="rgba(255, 69, 0, 0)" />
          </linearGradient>
          <filter id="glowLine">
            <feGaussianBlur stdDeviation="1.5" result="coloredBlur"/>
            <feMerge>
              <feMergeNode in="coloredBlur"/>
              <feMergeNode in="SourceGraphic"/>
            </feMerge>
          </filter>
        </defs>

        {/* Static Background Lines */}
        {paths.map((path, i) => (
          <path
            key={`bg-${i}`}
            d={getPathData(path.from, path.to)}
            fill="none"
            stroke="rgba(255,255,255,0.1)"
            strokeWidth="0.5"
          />
        ))}

        {/* Animated Flow Lines */}
        {paths.map((path, i) => (
          <motion.path
            key={`animated-${i}`}
            d={getPathData(path.from, path.to)}
            fill="none"
            stroke="url(#flowGradient)"
            strokeWidth="1"
            filter="url(#glowLine)"
            initial={{ pathLength: 0, opacity: 0 }}
            animate={{ 
              pathLength: [0, 1, 1],
              opacity: [0, 1, 0]
            }}
            transition={{
              duration: 2.5,
              repeat: Infinity,
              ease: "easeInOut",
              delay: i * 0.4, // Stagger delays based on position
            }}
          />
        ))}
      </svg>

      {/* Nodes */}
      {nodes.map((node, i) => (
        <motion.div
          key={node.id}
          className="absolute flex flex-col items-center justify-center transform -translate-x-1/2 -translate-y-1/2"
          style={{ left: `${node.x}%`, top: `${(node.y / 600) * 100}%` }}
          initial={{ scale: 0, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          transition={{ delay: i * 0.1 + 0.5, type: "spring", stiffness: 200 }}
        >
          <div className="relative">
            <motion.div 
              className="absolute inset-0 bg-primary/20 rounded-xl blur-md"
              animate={{ opacity: [0.3, 0.7, 0.3], scale: [1, 1.2, 1] }}
              transition={{ duration: 2, repeat: Infinity, delay: i * 0.2 }}
            />
            <div className={`relative h-12 w-12 rounded-xl bg-card border border-border shadow-lg flex items-center justify-center z-10 ${node.color}`}>
              <node.icon className="h-6 w-6" />
            </div>
          </div>
          <p className="mt-2 text-[10px] font-semibold text-muted-foreground whitespace-nowrap bg-background/80 px-2 py-0.5 rounded backdrop-blur-sm border border-border/50">
            {node.label}
          </p>
        </motion.div>
      ))}
    </div>
  )
}
