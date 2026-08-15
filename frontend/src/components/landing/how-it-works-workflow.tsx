"use client"

import { motion } from "framer-motion"
import { Box, Search, ShieldCheck, Zap } from "lucide-react"

const workflowSteps = [
  {
    number: "01",
    phase: "UNDERSTAND",
    icon: Box,
    description: "We analyze the repository, the pull request, and the architectural context.",
  },
  {
    number: "02",
    phase: "ANALYZE",
    icon: Search,
    description: "Specialized agents perform parallel analysis across security, quality and design.",
  },
  {
    number: "03",
    phase: "VALIDATE",
    icon: ShieldCheck,
    description: "Deterministic checks and scoring ensure consistency and trust.",
  },
  {
    number: "04",
    phase: "ACT",
    icon: Zap,
    description: "Findings, recommendations, and HITL approvals drive confident outcomes.",
  },
]

export function HowItWorksWorkflow() {
  return (
    <section id="how-it-works" className="py-24 md:py-32 relative bg-surface-dark">
      <div className="max-w-7xl mx-auto px-6 sm:px-8 lg:px-12">
        {/* Section heading. Carries the section semantically so the step cards
            below can sit at h3 without skipping a level. */}
        <div className="mb-16 md:mb-20">
          <h2 className="text-3xl sm:text-4xl lg:text-5xl font-black tracking-tight text-surface-dark-fg uppercase leading-[1.05] font-sans max-w-3xl">
            How Ignition works
          </h2>
        </div>

        {/* 4-Stage Horizontal Pipeline */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-10 md:gap-8 relative">
          {workflowSteps.map((step, idx) => {
            const Icon = step.icon
            return (
              <motion.div
                key={step.number}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.4, delay: idx * 0.1 }}
                className="relative flex flex-col gap-5"
              >
                {/* Top Icon & Connecting Line */}
                <div className="flex items-center">
                  <div className="h-14 w-14 rounded-full bg-surface-dark-panel border border-surface-dark-border-strong flex items-center justify-center text-surface-dark-fg shadow-md z-10 shrink-0">
                    <Icon className="h-5 w-5 text-surface-dark-fg" />
                  </div>

                  {/* Horizontal Orange Connector Line with Arrow for desktop */}
                  {idx < workflowSteps.length - 1 && (
                    <div className="hidden md:flex flex-1 items-center px-2">
                      <div className="h-px flex-1 bg-gradient-to-r from-primary/60 to-primary/30" />
                      <div className="w-1.5 h-1.5 border-t border-r border-primary transform rotate-45 -ml-1" />
                    </div>
                  )}
                </div>

                {/* Content */}
                <div className="flex flex-col gap-2 pt-2">
                  <span className="font-mono text-xs font-bold text-primary">{step.number}</span>
                  <h3 className="text-lg font-bold text-surface-dark-fg uppercase font-sans tracking-wide">
                    {step.phase}
                  </h3>
                  <p className="text-xs sm:text-sm text-surface-dark-muted leading-relaxed">
                    {step.description}
                  </p>
                </div>
              </motion.div>
            )
          })}
        </div>
      </div>
    </section>
  )
}
