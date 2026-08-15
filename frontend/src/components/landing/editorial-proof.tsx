"use client"

import { motion } from "framer-motion"

const proofPoints = [
  {
    value: "04",
    unit: "agents",
    label: "Parallel Specialist Nodes",
    description: "Structural, Logic, Security, and Critic agents run concurrently on every PR.",
  },
  {
    value: "<60s",
    unit: "latency",
    label: "Average Review Latency",
    description: "Fast parallel orchestration ensures developer CI pipelines never stall.",
  },
  {
    value: "100%",
    unit: "verified",
    label: "Deterministic AST Validation",
    description: "Static syntax trees and explicit schemas eliminate LLM hallucinations.",
  },
  {
    value: "94",
    unit: "/ 100",
    label: "Target ACS Standard",
    description: "Mathematical Architecture Compliance Score tracking code health over time.",
  },
]

export function EditorialProof() {
  return (
    <section className="py-28 md:py-36 relative border-y border-white/[0.06] bg-black/20">
      <div className="max-w-7xl mx-auto px-6 sm:px-8 lg:px-12">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-10 lg:gap-12">
          {proofPoints.map((item, idx) => (
            <motion.div
              key={item.label}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.4, delay: idx * 0.1 }}
              className="flex flex-col gap-3"
            >
              <div className="flex items-baseline gap-1.5 font-mono">
                <span className="text-5xl sm:text-6xl font-black text-foreground tracking-tight tabular-nums">
                  {item.value}
                </span>
                <span className="text-sm font-bold text-primary uppercase">{item.unit}</span>
              </div>
              <h3 className="text-base font-bold text-foreground uppercase font-sans">
                {item.label}
              </h3>
              <p className="text-xs sm:text-sm text-muted-foreground leading-relaxed">
                {item.description}
              </p>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  )
}
