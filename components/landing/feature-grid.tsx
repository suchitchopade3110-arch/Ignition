"use client"

import { motion } from "framer-motion"
import { Layers, ShieldCheck, GitMerge, Zap, Users, BarChart3, Fingerprint, Sparkles } from "lucide-react"

const features = [
  {
    title: "Architecture Intelligence",
    description: "Detects SOLID principle violations and anti-patterns before they merge into main.",
    icon: Layers,
    colSpan: "md:col-span-2",
  },
  {
    title: "Security Analysis",
    description: "Identifies OWASP top 10 vulnerabilities deep within complex logic flows.",
    icon: ShieldCheck,
    colSpan: "md:col-span-1",
  },
  {
    title: "Logic Validation",
    description: "Traces execution paths to find race conditions and chaotic state.",
    icon: GitMerge,
    colSpan: "md:col-span-1",
  },
  {
    title: "Performance Detection",
    description: "Flags N+1 queries, memory leaks, and inefficient algorithms.",
    icon: Zap,
    colSpan: "md:col-span-1",
  },
  {
    title: "Human-in-the-Loop",
    description: "Hard gates require manual human approval for critical severity issues.",
    icon: Users,
    colSpan: "md:col-span-1",
  },
  {
    title: "Architecture Score",
    description: "Tracks the long-term health and technical debt of your repositories.",
    icon: BarChart3,
    colSpan: "md:col-span-2",
  },
  {
    title: "Deterministic Validation",
    description: "No hallucinated review comments. Every finding is backed by static analysis and verifiable context.",
    icon: Fingerprint,
    colSpan: "md:col-span-2",
  },
  {
    title: "Auto Fix Suggestions",
    description: "Agents don't just point out flaws; they generate the precise code diff needed to fix them.",
    icon: Sparkles,
    colSpan: "md:col-span-1",
  }
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
            className="text-lg text-muted-foreground max-w-2xl mx-auto"
          >
            Ignition combines the precision of static analysis with the reasoning capabilities of multi-agent LLMs to deliver code reviews you can actually trust.
          </motion.p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {features.map((feature, i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: i * 0.1 }}
              className={`group relative overflow-hidden rounded-2xl bg-card border border-border p-8 hover:border-primary/50 transition-colors duration-500 ${feature.colSpan}`}
            >
              {/* Hover Glow */}
              <div className="absolute inset-0 bg-gradient-to-br from-primary/10 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500 pointer-events-none" />
              
              <div className="relative z-10 flex flex-col h-full">
                <div className="mb-6 inline-flex h-12 w-12 items-center justify-center rounded-xl bg-secondary border border-border text-primary shadow-sm group-hover:scale-110 group-hover:bg-primary group-hover:text-primary-foreground group-hover:border-primary transition-all duration-500">
                  <feature.icon className="h-6 w-6" />
                </div>
                <h3 className="text-xl font-bold text-foreground mb-3">{feature.title}</h3>
                <p className="text-muted-foreground leading-relaxed mt-auto">
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
