"use client"

import { motion } from "framer-motion"
import { GitPullRequest, ShieldCheck, Activity, ArrowUpRight } from "lucide-react"
import Link from "next/link"
import { GithubSuggestionCatch } from "@/components/landing/github-suggestion-catch"

export function EditorialProductShowcase() {
  return (
    <section id="product" className="py-32 md:py-44 relative bg-black/20 border-y border-white/[0.06]">
      <div className="max-w-7xl mx-auto px-6 sm:px-8 lg:px-12">
        {/* Section Header */}
        <div className="flex flex-col md:flex-row md:items-end justify-between mb-16 gap-8">
          <div className="flex flex-col gap-4 max-w-2xl">
            <span className="text-xs font-mono font-bold tracking-widest text-primary uppercase">
              04 / Verified Findings
            </span>
            <h2 className="text-4xl sm:text-5xl lg:text-6xl font-extrabold tracking-tight text-foreground uppercase font-sans">
              Precision in action. <br />
              <span className="text-muted-foreground">Deterministic fixes in GitHub.</span>
            </h2>
            <p className="text-base sm:text-lg text-muted-foreground leading-relaxed">
              Ignition doesn&apos;t produce generic summaries. It pinpoints the exact file coordinates, explains the root cause, and generates clean GitHub suggestion blocks for one-click commit.
            </p>
          </div>

          <Link
            href="/login"
            className="group flex items-center gap-2 text-xs font-mono uppercase tracking-wider text-primary hover:text-primary/80 transition-colors shrink-0"
          >
            <span>Inspect Live In App</span>
            <ArrowUpRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5 group-hover:-translate-y-0.5" />
          </Link>
        </div>

        {/* Live Product Showcase Frame (Level 1 Subtle Glass) */}
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6 }}
          className="bg-card/60 backdrop-blur-md border border-white/[0.08] rounded-2xl sm:rounded-3xl p-4 sm:p-8 lg:p-10 shadow-[inset_0_1px_0_0_rgba(255,255,255,0.03)]"
        >
          {/* PR Meta Bar */}
          <div className="flex flex-wrap items-center justify-between gap-4 pb-6 mb-6 border-b border-white/[0.06] font-mono text-xs">
            <div className="flex items-center gap-3">
              <span className="p-2 rounded-lg bg-primary/10 text-primary border border-primary/20">
                <GitPullRequest className="h-4 w-4" />
              </span>
              <div>
                <div className="text-foreground font-bold text-sm">PR #142: optimize database ledger queries</div>
                <div className="text-muted-foreground text-[11px]">Branch: feature/payment-speedup • Commit: 8fa3c01</div>
              </div>
            </div>

            <div className="flex items-center gap-4">
              <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-background/60 border border-white/[0.06]">
                <Activity className="h-3.5 w-3.5 text-primary" />
                <span className="text-muted-foreground">ACS:</span>
                <span className="font-bold text-foreground">94/100</span>
              </div>
              <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                <ShieldCheck className="h-3.5 w-3.5" />
                <span>Deterministic Pass</span>
              </div>
            </div>
          </div>

          {/* Inline GitHub Suggestion & Code Diff (Level 0 Flat Content) */}
          <div className="rounded-xl overflow-hidden border border-white/[0.06]">
            <GithubSuggestionCatch />
          </div>
        </motion.div>
      </div>
    </section>
  )
}
