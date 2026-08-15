"use client"

import { motion } from "framer-motion"
import { Cpu, ShieldAlert, UserCheck, TrendingUp } from "lucide-react"

/**
 * Capabilities sit on an asymmetric 12-column grid (7/5 then 5/7) so the rows
 * counterweight each other instead of repeating one uniform cell four times.
 * Everything collapses to a single column below `lg`.
 */
const capabilities = [
  {
    icon: Cpu,
    title: "AUTONOMOUS ANALYSIS",
    description:
      "Multi-agent system that understands your repository, pull requests, intent, and architecture.",
    span: "lg:col-span-7",
  },
  {
    icon: ShieldAlert,
    title: "SECURITY & QUALITY INTELLIGENCE",
    description:
      "Detect vulnerabilities, design flaws, regressions, and anti-patterns with high precision.",
    span: "lg:col-span-5",
  },
  {
    icon: UserCheck,
    title: "HUMAN IN THE LOOP",
    description:
      "Critical findings are routed to the right humans for fast, confident decisions.",
    span: "lg:col-span-5",
  },
  {
    icon: TrendingUp,
    title: "CONTINUOUS IMPROVEMENT",
    description:
      "Data-driven insights and feedback loops that make your engineering practice better every day.",
    span: "lg:col-span-7",
  },
]

export function CoreCapabilitiesGrid() {
  return (
    <section
      id="capabilities"
      className="py-24 md:py-32 relative bg-surface-dark border-t border-surface-dark-border"
    >
      <div className="max-w-7xl mx-auto px-6 sm:px-8 lg:px-12">
        <div className="mb-16 md:mb-20">
          <h2 className="text-3xl sm:text-4xl lg:text-5xl font-black tracking-tight text-surface-dark-fg uppercase leading-[1.05] font-sans max-w-3xl">
            Core capabilities
          </h2>
        </div>

        {/* gap-px over a border-coloured backing plate draws the hairline rules */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-px bg-surface-dark-border">
          {capabilities.map((cap, idx) => {
            const Icon = cap.icon
            return (
              <motion.div
                key={cap.title}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.4, delay: idx * 0.1 }}
                className={`${cap.span} flex flex-col gap-4 bg-surface-dark p-8 lg:p-10`}
              >
                <div className="text-primary">
                  <Icon className="h-7 w-7 stroke-[1.5]" />
                </div>

                <h3 className="text-base font-bold text-surface-dark-fg uppercase font-sans tracking-wide leading-snug">
                  {cap.title}
                </h3>

                <p className="text-xs sm:text-sm text-surface-dark-muted leading-relaxed max-w-prose">
                  {cap.description}
                </p>
              </motion.div>
            )
          })}
        </div>
      </div>
    </section>
  )
}
