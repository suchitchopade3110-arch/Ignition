"use client"

import { motion } from "framer-motion"

export function EditorialManifesto() {
  return (
    <section className="py-28 md:py-44 relative border-y border-white/[0.06] bg-black/20">
      <div className="max-w-7xl mx-auto px-6 sm:px-8 lg:px-12">
        <div className="flex flex-col gap-10 max-w-5xl">
          <motion.div
            initial={{ opacity: 0, y: 15 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            className="flex items-center gap-3"
          >
            <span className="text-xs font-mono font-bold tracking-widest text-primary uppercase">
              02 / The Philosophy
            </span>
            <span className="h-px w-8 bg-white/[0.12]" />
            <span className="text-xs font-mono text-muted-foreground uppercase tracking-widest">
              Manifesto
            </span>
          </motion.div>

          <motion.h2
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5, delay: 0.1 }}
            className="text-3xl sm:text-5xl lg:text-6xl font-extrabold tracking-tight text-foreground leading-[1.08] uppercase font-sans select-none"
          >
            Code review is not a checkbox. <br />
            <span className="text-transparent bg-clip-text bg-linear-to-r from-foreground via-muted-foreground to-muted-foreground/60">
              It is a continuous engineering system.
            </span>
          </motion.h2>

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5, delay: 0.2 }}
            className="grid grid-cols-1 md:grid-cols-12 gap-8 pt-4 items-start"
          >
            <div className="md:col-span-4 font-mono text-xs text-primary uppercase tracking-wider font-semibold">
              Deterministic over Probabilistic
            </div>
            <div className="md:col-span-8 text-base sm:text-lg text-muted-foreground leading-relaxed">
              Conventional linters flood pull requests with noisy syntax warnings. Monolithic language models hallucinate non-existent methods and miss subtle race conditions. Ignition replaces guesswork with isolated abstract syntax tree parsing and specialized deterministic critic nodes — delivering reproducible, actionable code fixes directly into engineering workflows.
            </div>
          </motion.div>
        </div>
      </div>
    </section>
  )
}
