"use client"

import { motion } from "framer-motion"

const impactMetrics = [
  { value: "60%", label: "Less review time" },
  { value: "90%", label: "Vulnerability detection" },
  { value: "< 60s", label: "Average review time" },
  { value: "24/7", label: "Continuous coverage" },
  { value: "10x", label: "More consistent reviews" },
]

export function EngineeringImpactStrip() {
  return (
    <section className="py-24 md:py-28 relative bg-surface-light text-surface-light-fg">
      <div className="max-w-7xl mx-auto px-6 sm:px-8 lg:px-12">
        <div className="mb-14">
          <h2 className="text-h2 tracking-tight text-surface-light-fg uppercase font-sans max-w-3xl">
            Engineering impact
          </h2>
        </div>

        {/* 5-Column Metrics Strip with Dividers */}
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 divide-y sm:divide-y-0 lg:divide-x divide-surface-light-border -mx-4 px-4">
          {impactMetrics.map((item, idx) => (
            <motion.div
              key={item.label}
              initial={{ opacity: 0, y: 15 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.4, delay: idx * 0.08 }}
              className="flex flex-col gap-2 py-6 sm:py-4 lg:py-0 lg:px-6 first:pl-0 last:pr-0"
            >
              <span className="text-4xl sm:text-5xl font-black text-primary font-mono tabular-nums tracking-tight">
                {item.value}
              </span>
              <span className="text-xs sm:text-sm font-medium text-surface-light-muted leading-snug">
                {item.label}
              </span>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  )
}
