"use client"

import { motion } from "framer-motion"

const stackItems = [
  "GitHub App API",
  "LangGraph Runtime",
  "FastAPI",
  "Next.js 15",
  "PostgreSQL",
  "AST Parsers",
]

export function EditorialEcosystem() {
  return (
    <section className="py-20 relative">
      <div className="max-w-7xl mx-auto px-6 sm:px-8 lg:px-12">
        <div className="flex flex-col items-center text-center gap-6">
          <span className="text-[11px] font-mono uppercase tracking-widest text-muted-foreground">
            Built with modern open-source & enterprise infrastructure
          </span>
          <div className="flex flex-wrap items-center justify-center gap-3 sm:gap-4">
            {stackItems.map((item, idx) => (
              <motion.span
                key={item}
                initial={{ opacity: 0, scale: 0.95 }}
                whileInView={{ opacity: 1, scale: 1 }}
                viewport={{ once: true }}
                transition={{ duration: 0.3, delay: idx * 0.05 }}
                className="px-4 py-2 rounded-lg bg-white/[0.02] border border-white/[0.06] text-xs font-mono text-muted-foreground uppercase tracking-wider hover:text-foreground hover:border-white/[0.12] transition-colors"
              >
                {item}
              </motion.span>
            ))}
          </div>
        </div>
      </div>
    </section>
  )
}
