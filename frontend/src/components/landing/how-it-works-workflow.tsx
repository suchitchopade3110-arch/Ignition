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
    <section id="how-it-works" className="py-24 md:py-32 relative bg-[#090A0B]">
      <div className="max-w-7xl mx-auto px-6 sm:px-8 lg:px-12">
        {/* Section Category Header */}
        <div className="mb-16 md:mb-20">
          <span className="font-mono text-xs text-[#FF4D0A] uppercase tracking-widest font-bold">
            02 / HOW IGNITION WORKS
          </span>
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
                  <div className="h-14 w-14 rounded-full bg-[#121416] border border-[#292D31] flex items-center justify-center text-[#F4F3EF] shadow-md z-10 shrink-0">
                    <Icon className="h-5 w-5 text-[#F4F3EF]" />
                  </div>

                  {/* Horizontal Orange Connector Line with Arrow for desktop */}
                  {idx < workflowSteps.length - 1 && (
                    <div className="hidden md:flex flex-1 items-center px-2">
                      <div className="h-px flex-1 bg-gradient-to-r from-[#FF4D0A]/60 to-[#FF4D0A]/30" />
                      <div className="w-1.5 h-1.5 border-t border-r border-[#FF4D0A] transform rotate-45 -ml-1" />
                    </div>
                  )}
                </div>

                {/* Content */}
                <div className="flex flex-col gap-2 pt-2">
                  <span className="font-mono text-xs font-bold text-[#FF4D0A]">{step.number}</span>
                  <h3 className="text-lg font-bold text-[#F4F3EF] uppercase font-sans tracking-wide">
                    {step.phase}
                  </h3>
                  <p className="text-xs sm:text-sm text-[#9A9C9F] leading-relaxed">
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
