"use client"

import { motion } from "framer-motion"
import { Layers, ShieldCheck, GitMerge, Zap, Users, BarChart3, Fingerprint, Sparkles } from "lucide-react"

const features = [
  {
    title: "Architecture Intelligence",
    description: "Detects SOLID principle violations, structural anti-patterns, and layer leakage before pull requests merge into main.",
    icon: Layers,
    colSpan: "md:col-span-2",
  },
  {
    title: "Security & Vulnerability Analysis",
    description: "Identifies OWASP top 10 flaws, secret leakage, and supply chain exposure across full call graphs.",
    icon: ShieldCheck,
    colSpan: "md:col-span-1",
  },
  {
    title: "Deterministic Validation",
    description: "Every finding is backed by AST static analysis and verifiable context. Zero hallucinated commentary.",
    icon: Fingerprint,
    colSpan: "md:col-span-1",
  },
  {
    title: "Logic & Concurrency Checks",
    description: "Traces asynchronous execution paths to catch race conditions, unhandled rejections, and chaotic state bugs.",
    icon: GitMerge,
    colSpan: "md:col-span-2",
  },
  {
    title: "Performance Detection",
    description: "Flags N+1 database queries, memory leaks, and inefficient algorithms before deployment.",
    icon: Zap,
    colSpan: "md:col-span-1",
  },
  {
    title: "Human-in-the-Loop Gate",
    description: "Deterministic policy gates require manual human sign-off for critical severity issues or score drops.",
    icon: Users,
    colSpan: "md:col-span-1",
  },
  {
    title: "Architecture Compliance Score",
    description: "Continuously tracks repository health, regressions, and technical debt trends across release cycles.",
    icon: BarChart3,
    colSpan: "md:col-span-1",
  },
  {
    title: "Auto-Fix Suggestions",
    description: "Synthesizes verified code diffs with exact line replacements for immediate one-click remediation.",
    icon: Sparkles,
    colSpan: "md:col-span-3",
  },
]

export function FeatureGrid() {
  return (
    <section id="features" className="py-24 relative z-10">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center mb-16">
          <motion.h2
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            className="text-3xl md:text-4xl font-bold tracking-tight text-foreground mb-4"
          >
            Engineering Excellence, Automated.
          </motion.h2>
          <motion.p
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ delay: 0.1 }}
            className="text-base sm:text-lg text-muted-foreground max-w-2xl mx-auto"
          >
            Ignition combines static analysis with multi-agent reasoning to deliver code reviews engineering teams can trust.
          </motion.p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {features.map((feature, i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: i * 0.08 }}
              className={`group relative overflow-hidden rounded-2xl bg-card border border-border p-8 hover:border-primary/50 transition-colors duration-300 ${feature.colSpan}`}
            >
              <div className="relative z-10 flex flex-col h-full">
                <div className="mb-6 inline-flex h-12 w-12 items-center justify-center rounded-xl bg-secondary border border-border text-primary group-hover:bg-primary group-hover:text-primary-foreground group-hover:border-primary transition-all duration-300">
                  <feature.icon className="h-6 w-6" />
                </div>
                <h3 className="text-xl font-bold text-foreground mb-2">{feature.title}</h3>
                <p className="text-sm text-muted-foreground leading-relaxed mt-auto">
                  {feature.description}
                </p>
              </div>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  )
}
