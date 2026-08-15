"use client"

import { motion } from "framer-motion"
import { Database, ShieldAlert, Cpu, UserCheck, CheckCircle2 } from "lucide-react"

export function EditorialCapabilities() {
  return (
    <section id="capabilities" className="py-32 md:py-44 relative">
      <div className="max-w-7xl mx-auto px-6 sm:px-8 lg:px-12">
        {/* Section Header */}
        <div className="flex flex-col gap-4 mb-24 md:mb-32 max-w-3xl">
          <span className="text-xs font-mono font-bold tracking-widest text-primary uppercase">
            03 / System Architecture
          </span>
          <h2 className="text-4xl sm:text-5xl lg:text-6xl font-extrabold tracking-tight text-foreground uppercase font-sans">
            Core capabilities, <br />
            <span className="text-muted-foreground">engineered for certainty.</span>
          </h2>
          <p className="text-base sm:text-lg text-muted-foreground leading-relaxed pt-2">
            Each layer of the Ignition multi-agent graph serves an isolated, verifiable function in your code review pipeline.
          </p>
        </div>

        {/* Editorial Sequence: Alternating Flow */}
        <div className="space-y-32 md:space-y-44">
          {/* Capability 01: Deep Repository Intelligence */}
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-12 lg:gap-16 items-center">
            <motion.div
              initial={{ opacity: 0, x: -20 }}
              whileInView={{ opacity: 1, x: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5 }}
              className="lg:col-span-6 flex flex-col gap-6"
            >
              <div className="font-mono text-4xl sm:text-5xl font-black text-primary/80">01</div>
              <h3 className="text-2xl sm:text-3xl lg:text-4xl font-bold text-foreground uppercase font-sans">
                Repository Intelligence & AST Parsing
              </h3>
              <p className="text-base text-muted-foreground leading-relaxed">
                Ignition constructs comprehensive abstract syntax trees (ASTs) and dependency call graphs across your entire codebase. Rather than evaluating pull request diffs in a vacuum, the system traces imported symbols, inheritance hierarchies, and database schema mappings.
              </p>
              <ul className="space-y-2.5 font-mono text-xs text-foreground/90 pt-2">
                <li className="flex items-center gap-2">
                  <CheckCircle2 className="h-4 w-4 text-primary shrink-0" />
                  <span>Full AST tree generation before model inference</span>
                </li>
                <li className="flex items-center gap-2">
                  <CheckCircle2 className="h-4 w-4 text-primary shrink-0" />
                  <span>Inter-module import and circular dependency tracing</span>
                </li>
                <li className="flex items-center gap-2">
                  <CheckCircle2 className="h-4 w-4 text-primary shrink-0" />
                  <span>Zero retention of customer source code on disk</span>
                </li>
              </ul>
            </motion.div>

            <motion.div
              initial={{ opacity: 0, x: 20 }}
              whileInView={{ opacity: 1, x: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5 }}
              className="lg:col-span-6"
            >
              <div className="bg-card/60 backdrop-blur-md border border-white/[0.08] rounded-2xl p-6 sm:p-8 shadow-[inset_0_1px_0_0_rgba(255,255,255,0.03)] font-mono text-xs">
                <div className="flex items-center justify-between pb-4 border-b border-white/[0.06] text-muted-foreground">
                  <span className="flex items-center gap-2">
                    <Database className="h-4 w-4 text-primary" />
                    context_parser.rs
                  </span>
                  <span className="text-[10px] text-emerald-400">AST_GENERATED</span>
                </div>
                <div className="py-4 space-y-2 text-muted-foreground">
                  <div className="text-foreground font-semibold">→ Resolving Module Dependencies:</div>
                  <div className="pl-4 border-l border-white/[0.08] space-y-1">
                    <div>├── app.core.security.jwt_handler (AST Level 3)</div>
                    <div>├── app.db.models.user_account (Schema Verified)</div>
                    <div>└── app.api.v1.auth.routes (Controller Node)</div>
                  </div>
                  <div className="pt-2 text-primary">✓ Call graph context enriched with 14 referenced definitions</div>
                </div>
              </div>
            </motion.div>
          </div>

          {/* Capability 02: Parallel Specialist Fan-Out */}
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-12 lg:gap-16 items-center">
            <motion.div
              initial={{ opacity: 0, x: -20 }}
              whileInView={{ opacity: 1, x: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5 }}
              className="lg:col-span-6 order-2 lg:order-1"
            >
              <div className="bg-card/60 backdrop-blur-md border border-white/[0.08] rounded-2xl p-6 sm:p-8 shadow-[inset_0_1px_0_0_rgba(255,255,255,0.03)] font-mono text-xs space-y-3">
                <div className="flex items-center justify-between pb-3 border-b border-white/[0.06] text-muted-foreground">
                  <span className="flex items-center gap-2">
                    <Cpu className="h-4 w-4 text-primary" />
                    langgraph_orchestrator
                  </span>
                  <span className="text-[10px] text-primary">PARALLEL_EXECUTION</span>
                </div>
                <div className="grid grid-cols-1 gap-2.5">
                  <div className="p-3 rounded-lg bg-background/50 border border-white/[0.04] flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className="h-2 w-2 rounded-full bg-emerald-400" />
                      <span className="text-foreground">Structural & SOLID Inspector</span>
                    </div>
                    <span className="text-[10px] text-muted-foreground">0.8s</span>
                  </div>
                  <div className="p-3 rounded-lg bg-background/50 border border-white/[0.04] flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className="h-2 w-2 rounded-full bg-amber-400" />
                      <span className="text-foreground">Logic & Race Condition Assessor</span>
                    </div>
                    <span className="text-[10px] text-muted-foreground">1.2s</span>
                  </div>
                  <div className="p-3 rounded-lg bg-background/50 border border-white/[0.04] flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className="h-2 w-2 rounded-full bg-red-400" />
                      <span className="text-foreground">OWASP Vulnerability Auditor</span>
                    </div>
                    <span className="text-[10px] text-muted-foreground">0.9s</span>
                  </div>
                </div>
              </div>
            </motion.div>

            <motion.div
              initial={{ opacity: 0, x: 20 }}
              whileInView={{ opacity: 1, x: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5 }}
              className="lg:col-span-6 order-1 lg:order-2 flex flex-col gap-6"
            >
              <div className="font-mono text-4xl sm:text-5xl font-black text-primary/80">02</div>
              <h3 className="text-2xl sm:text-3xl lg:text-4xl font-bold text-foreground uppercase font-sans">
                Parallel Specialist Agent Fan-Out
              </h3>
              <p className="text-base text-muted-foreground leading-relaxed">
                Rather than burdening a single monolithic prompt, Ignition forks analysis to specialized, sandboxed agents. Architecture inspectors, race-condition investigators, and security auditors execute concurrently across their respective domains.
              </p>
              <ul className="space-y-2.5 font-mono text-xs text-foreground/90 pt-2">
                <li className="flex items-center gap-2">
                  <CheckCircle2 className="h-4 w-4 text-primary shrink-0" />
                  <span>Independent domain-specific prompt and rule isolation</span>
                </li>
                <li className="flex items-center gap-2">
                  <CheckCircle2 className="h-4 w-4 text-primary shrink-0" />
                  <span>Concurrent LangGraph node execution reduces latency</span>
                </li>
                <li className="flex items-center gap-2">
                  <CheckCircle2 className="h-4 w-4 text-primary shrink-0" />
                  <span>Hard bounded recursion cap prevents infinite self-correction</span>
                </li>
              </ul>
            </motion.div>
          </div>

          {/* Capability 03: Deterministic Critic & ACS */}
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-12 lg:gap-16 items-center">
            <motion.div
              initial={{ opacity: 0, x: -20 }}
              whileInView={{ opacity: 1, x: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5 }}
              className="lg:col-span-6 flex flex-col gap-6"
            >
              <div className="font-mono text-4xl sm:text-5xl font-black text-primary/80">03</div>
              <h3 className="text-2xl sm:text-3xl lg:text-4xl font-bold text-foreground uppercase font-sans">
                Critic Synthesis & Architecture Compliance Score
              </h3>
              <p className="text-base text-muted-foreground leading-relaxed">
                Before any suggestion surfaces, the Critic agent conducts a secondary verification pass. It deduplicates overlapping findings, checks code proposals against deterministic syntax rules, and computes the repository Architecture Compliance Score (ACS).
              </p>
              <ul className="space-y-2.5 font-mono text-xs text-foreground/90 pt-2">
                <li className="flex items-center gap-2">
                  <CheckCircle2 className="h-4 w-4 text-primary shrink-0" />
                  <span>Zero-hallucination verification filter on all code fixes</span>
                </li>
                <li className="flex items-center gap-2">
                  <CheckCircle2 className="h-4 w-4 text-primary shrink-0" />
                  <span>Mathematical ACS grading based on weighted issue severity</span>
                </li>
                <li className="flex items-center gap-2">
                  <CheckCircle2 className="h-4 w-4 text-primary shrink-0" />
                  <span>Exact GitHub inline suggestion markdown generation</span>
                </li>
              </ul>
            </motion.div>

            <motion.div
              initial={{ opacity: 0, x: 20 }}
              whileInView={{ opacity: 1, x: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5 }}
              className="lg:col-span-6"
            >
              <div className="bg-card/60 backdrop-blur-md border border-white/[0.08] rounded-2xl p-6 sm:p-8 shadow-[inset_0_1px_0_0_rgba(255,255,255,0.03)] font-mono text-xs flex flex-col gap-4">
                <div className="flex items-center justify-between pb-3 border-b border-white/[0.06] text-muted-foreground">
                  <span className="flex items-center gap-2">
                    <ShieldAlert className="h-4 w-4 text-primary" />
                    critic_synthesizer.py
                  </span>
                  <span className="text-[10px] text-emerald-400 font-bold">ACS: 94 / 100</span>
                </div>
                <div className="p-4 rounded-xl bg-background/50 border border-white/[0.04] space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-foreground font-semibold">Raw Findings Flagged:</span>
                    <span className="text-muted-foreground">11 items</span>
                  </div>
                  <div className="flex items-center justify-between text-muted-foreground">
                    <span>False Positives Pruned:</span>
                    <span className="text-emerald-400">4 duplicates filtered</span>
                  </div>
                  <div className="flex items-center justify-between text-primary font-bold border-t border-white/[0.06] pt-2">
                    <span>Verified Actionable Findings:</span>
                    <span>7 published</span>
                  </div>
                </div>
              </div>
            </motion.div>
          </div>

          {/* Capability 04: Human-in-the-Loop Control */}
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-12 lg:gap-16 items-center">
            <motion.div
              initial={{ opacity: 0, x: -20 }}
              whileInView={{ opacity: 1, x: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5 }}
              className="lg:col-span-6 order-2 lg:order-1"
            >
              <div className="bg-card/60 backdrop-blur-md border border-white/[0.08] rounded-2xl p-6 sm:p-8 shadow-[inset_0_1px_0_0_rgba(255,255,255,0.03)] font-mono text-xs space-y-4">
                <div className="flex items-center justify-between pb-3 border-b border-white/[0.06] text-muted-foreground">
                  <span className="flex items-center gap-2">
                    <UserCheck className="h-4 w-4 text-primary" />
                    hitl_approval_queue
                  </span>
                  <span className="text-[10px] text-amber-400">PENDING_APPROVAL</span>
                </div>
                <div className="p-4 rounded-xl bg-background/50 border border-white/[0.04] space-y-3">
                  <div className="text-foreground font-semibold">High-Risk Architecture Decision:</div>
                  <p className="text-[11px] text-muted-foreground font-sans leading-relaxed">
                    Agent proposed database schema migration for <code className="text-primary">ledger_entries</code>. Requires team lead review before GitHub PR comment merge.
                  </p>
                  <div className="flex items-center gap-2 pt-1">
                    <span className="px-3 py-1 bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 rounded text-[10px] font-bold">
                      Approve & Comment
                    </span>
                    <span className="px-3 py-1 bg-white/[0.05] text-muted-foreground border border-white/[0.08] rounded text-[10px]">
                      Reject
                    </span>
                  </div>
                </div>
              </div>
            </motion.div>

            <motion.div
              initial={{ opacity: 0, x: 20 }}
              whileInView={{ opacity: 1, x: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5 }}
              className="lg:col-span-6 order-1 lg:order-2 flex flex-col gap-6"
            >
              <div className="font-mono text-4xl sm:text-5xl font-black text-primary/80">04</div>
              <h3 className="text-2xl sm:text-3xl lg:text-4xl font-bold text-foreground uppercase font-sans">
                Human-in-the-Loop Governance
              </h3>
              <p className="text-base text-muted-foreground leading-relaxed">
                Autonomous when safe, human when critical. Ignition lets engineering managers configure automated thresholds. Low-risk linting and non-breaking fixes publish automatically, while major architectural alterations route to the HITL approval queue.
              </p>
              <ul className="space-y-2.5 font-mono text-xs text-foreground/90 pt-2">
                <li className="flex items-center gap-2">
                  <CheckCircle2 className="h-4 w-4 text-primary shrink-0" />
                  <span>Configurable ACS severity thresholds for auto-publishing</span>
                </li>
                <li className="flex items-center gap-2">
                  <CheckCircle2 className="h-4 w-4 text-primary shrink-0" />
                  <span>One-click approval or rejection with custom feedback notes</span>
                </li>
                <li className="flex items-center gap-2">
                  <CheckCircle2 className="h-4 w-4 text-primary shrink-0" />
                  <span>Complete immutable review ledger for enterprise compliance</span>
                </li>
              </ul>
            </motion.div>
          </div>
        </div>
      </div>
    </section>
  )
}
