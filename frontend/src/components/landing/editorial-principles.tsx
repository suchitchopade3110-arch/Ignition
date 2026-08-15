"use client"

import { motion } from "framer-motion"

const principles = [
  {
    title: "Deterministic where possible.",
    statement:
      "Static analysis syntax trees and explicit rule engines precede any probabilistic model inference. We eliminate hallucinations before they begin.",
  },
  {
    title: "Explainable where necessary.",
    statement:
      "No opaque scores or vague advice. Every finding delivers exact file coordinates, architectural context, and verified drop-in code replacements.",
  },
  {
    title: "Autonomous when safe.",
    statement:
      "Non-breaking optimizations, performance fixes, and standard linting violations publish straight to the pull request to unblock developers instantly.",
  },
  {
    title: "Human when it matters.",
    statement:
      "High-impact schema migrations, destructive refactors, and sensitive security alterations pause in the HITL queue for team lead verification.",
  },
]

export function EditorialPrinciples() {
  return (
    <section id="principles" className="py-32 md:py-44 relative bg-black/20 border-y border-white/[0.06]">
      <div className="max-w-7xl mx-auto px-6 sm:px-8 lg:px-12">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-16 items-start">
          {/* Left Column: Manifesto Headline */}
          <div className="lg:col-span-5 flex flex-col gap-6 lg:sticky lg:top-32">
            <span className="text-xs font-mono font-bold tracking-widest text-primary uppercase">
              06 / Engineering Manifesto
            </span>
            <h2 className="text-4xl sm:text-5xl lg:text-6xl font-extrabold tracking-tight text-foreground uppercase font-sans leading-[1.02]">
              Built for <br />
              <span className="text-transparent bg-clip-text bg-linear-to-r from-primary via-orange-500 to-amber-500">
                engineers.
              </span>
            </h2>
            <p className="text-base sm:text-lg text-muted-foreground leading-relaxed">
              We built Ignition around a singular objective: delivering actionable, high-signal engineering reviews that development teams can trust implicitly.
            </p>
          </div>

          {/* Right Column: 4 Core Tenets */}
          <div className="lg:col-span-7 space-y-12">
            {principles.map((p, idx) => (
              <motion.div
                key={p.title}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.4, delay: idx * 0.1 }}
                className="flex flex-col gap-3 pb-8 border-b border-white/[0.06] last:border-0"
              >
                <div className="flex items-baseline gap-3">
                  <span className="font-mono text-xs font-bold text-primary">0{idx + 1}</span>
                  <h3 className="text-xl sm:text-2xl font-bold text-foreground uppercase font-sans">
                    {p.title}
                  </h3>
                </div>
                <p className="text-base text-muted-foreground leading-relaxed pl-7">
                  {p.statement}
                </p>
              </motion.div>
            ))}
          </div>
        </div>
      </div>
    </section>
  )
}
