"use client"

import { motion } from "framer-motion"
import { Search, GitFork, UserCheck, MessageSquarePlus } from "lucide-react"

const steps = [
  {
    number: "01",
    phase: "UNDERSTAND",
    title: "Repository Context & AST Mapping",
    description:
      "When a GitHub pull request webhook triggers, Ignition builds a full syntax graph. It analyzes the entire repository context—tracing imported definitions, schema references, and structural hierarchies beyond the isolated lines changed.",
    icon: Search,
    metrics: "AST Parsers • Call Graphs • Zero Code Retention",
  },
  {
    number: "02",
    phase: "ANALYZE",
    title: "Parallel Specialist Agent Fan-Out",
    description:
      "The task payload fans out to domain-isolated agent nodes. The Structural Inspector audits architecture patterns, the Logic Assessor identifies state mutations and race conditions, and the Security Auditor scans for OWASP vulnerabilities.",
    icon: GitFork,
    metrics: "LangGraph Runtime • 04 Parallel Nodes • Sandboxed Execution",
  },
  {
    number: "03",
    phase: "VALIDATE",
    title: "Deterministic Critic & ACS Calculation",
    description:
      "The Critic synthesizer deduplicates overlapping findings, filters out subjective noise, and validates proposed code fixes against deterministic syntax rules. It calculates the repository Architecture Compliance Score (ACS).",
    icon: UserCheck,
    metrics: "Strict False-Positive Filter • Bounded Self-Correction Cap",
  },
  {
    number: "04",
    phase: "ACT",
    title: "GitHub Suggestions & Governance",
    description:
      "Actionable recommendations publish directly to the pull request as native GitHub suggestion blocks. High-impact architectural changes or security anomalies route to the Human-in-the-Loop queue for engineer approval.",
    icon: MessageSquarePlus,
    metrics: "Inline Code Diffs • HITL Approval Queue • Immutable Ledger",
  },
]

export function EditorialMethodology() {
  return (
    <section id="methodology" className="py-32 md:py-44 relative">
      <div className="max-w-7xl mx-auto px-6 sm:px-8 lg:px-12">
        {/* Section Header */}
        <div className="flex flex-col gap-4 mb-24 md:mb-32 max-w-3xl">
          <span className="text-xs font-mono font-bold tracking-widest text-primary uppercase">
            05 / Methodology
          </span>
          <h2 className="text-4xl sm:text-5xl lg:text-6xl font-extrabold tracking-tight text-foreground uppercase font-sans">
            How Ignition <br />
            <span className="text-muted-foreground">reviews your codebase.</span>
          </h2>
          <p className="text-base sm:text-lg text-muted-foreground leading-relaxed pt-2">
            A four-stage deterministic orchestration pipeline designed to eliminate hallucinations and deliver verified code fixes.
          </p>
        </div>

        {/* Vertical Timeline Progression */}
        <div className="relative border-l border-white/[0.08] ml-4 sm:ml-8 pl-8 sm:pl-16 space-y-24 md:space-y-32">
          {/* Active Orange Progression Line */}
          <div className="absolute left-0 top-0 bottom-0 w-px bg-linear-to-b from-primary via-primary/50 to-transparent pointer-events-none" />

          {steps.map((step, idx) => {
            const Icon = step.icon
            return (
              <motion.div
                key={step.number}
                initial={{ opacity: 0, y: 25 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.5, delay: idx * 0.1 }}
                className="relative flex flex-col gap-6 group"
              >
                {/* Timeline Node Indicator */}
                <div className="absolute -left-12 sm:-left-20 top-0 flex items-center justify-center">
                  <div className="h-8 w-8 sm:h-9 sm:w-9 rounded-full bg-card border border-white/[0.12] flex items-center justify-center text-primary group-hover:border-primary group-hover:scale-110 transition-all shadow-[0_0_15px_rgba(255,69,0,0.2)]">
                    <Icon className="h-4 w-4" />
                  </div>
                </div>

                {/* Content Header */}
                <div className="flex items-center gap-3">
                  <span className="font-mono text-sm font-black text-primary">{step.number}</span>
                  <span className="h-px w-6 bg-white/[0.12]" />
                  <span className="font-mono text-xs uppercase tracking-widest text-muted-foreground">
                    {step.phase}
                  </span>
                </div>

                <h3 className="text-2xl sm:text-3xl lg:text-4xl font-bold text-foreground uppercase font-sans">
                  {step.title}
                </h3>

                <p className="text-base sm:text-lg text-muted-foreground leading-relaxed max-w-3xl">
                  {step.description}
                </p>

                <div className="font-mono text-xs text-foreground/80 bg-white/[0.02] border border-white/[0.06] rounded-lg px-4 py-2.5 w-fit">
                  {step.metrics}
                </div>
              </motion.div>
            )
          })}
        </div>
      </div>
    </section>
  )
}
