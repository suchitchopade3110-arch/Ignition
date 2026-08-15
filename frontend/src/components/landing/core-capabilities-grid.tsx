"use client"

import { motion } from "framer-motion"
import { Cpu, ShieldAlert, UserCheck, TrendingUp } from "lucide-react"

const capabilities = [
  {
    icon: Cpu,
    title: "AUTONOMOUS ANALYSIS",
    description:
      "Multi-agent system that understands your repository, pull requests, intent, and architecture.",
  },
  {
    icon: ShieldAlert,
    title: "SECURITY & QUALITY INTELLIGENCE",
    description:
      "Detect vulnerabilities, design flaws, regressions, and anti-patterns with high precision.",
  },
  {
    icon: UserCheck,
    title: "HUMAN IN THE LOOP",
    description:
      "Critical findings are routed to the right humans for fast, confident decisions.",
  },
  {
    icon: TrendingUp,
    title: "CONTINUOUS IMPROVEMENT",
    description:
      "Data-driven insights and feedback loops that make your engineering practice better every day.",
  },
]

export function CoreCapabilitiesGrid() {
  return (
    <section id="capabilities" className="py-24 md:py-32 relative bg-[#090A0B] border-t border-[#202326]">
      <div className="max-w-7xl mx-auto px-6 sm:px-8 lg:px-12">
        {/* Section Category Header */}
        <div className="mb-16 md:mb-20">
          <span className="font-mono text-xs text-[#FF4D0A] uppercase tracking-widest font-bold">
            03 / CORE CAPABILITIES
          </span>
        </div>

        {/* 4 Horizontally Separated Columns */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 divide-y lg:divide-y-0 lg:divide-x divide-[#202326] -mx-6 px-6">
          {capabilities.map((cap, idx) => {
            const Icon = cap.icon
            return (
              <motion.div
                key={cap.title}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.4, delay: idx * 0.1 }}
                className="flex flex-col gap-4 py-8 lg:py-0 lg:px-8 first:pl-0 last:pr-0"
              >
                <div className="text-[#FF4D0A]">
                  <Icon className="h-7 w-7 stroke-[1.5]" />
                </div>

                <h3 className="text-base font-bold text-[#F4F3EF] uppercase font-sans tracking-wide leading-snug">
                  {cap.title}
                </h3>

                <p className="text-xs sm:text-sm text-[#9A9C9F] leading-relaxed">
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
