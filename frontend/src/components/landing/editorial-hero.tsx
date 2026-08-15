"use client"

import Link from "next/link"
import { motion } from "framer-motion"
import { ArrowRight, ShieldCheck, Terminal, Cpu, GitPullRequest, CheckCircle2 } from "lucide-react"

export function EditorialHero() {
  return (
    <section className="relative pt-32 pb-24 md:pt-40 md:pb-36 overflow-hidden">
      <div className="max-w-7xl mx-auto px-6 sm:px-8 lg:px-12">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-12 lg:gap-16 items-start">
          {/* Left: Oversized Editorial Statement */}
          <div className="lg:col-span-7 flex flex-col gap-8">
            <motion.div
              initial={{ opacity: 0, y: 15 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.4 }}
              className="flex items-center gap-3"
            >
              <span className="text-xs font-mono font-bold tracking-widest text-primary uppercase">
                01 / Code Intelligence
              </span>
              <span className="h-px w-8 bg-white/[0.12]" />
              <span className="text-xs font-mono text-muted-foreground uppercase tracking-widest">
                Deterministic Agent Graph
              </span>
            </motion.div>

            <motion.h1
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: 0.1 }}
              className="text-5xl sm:text-7xl lg:text-8xl font-extrabold tracking-tight text-foreground leading-[0.95] uppercase font-sans select-none"
            >
              Your codebase <br />
              <span className="text-transparent bg-clip-text bg-linear-to-r from-foreground via-foreground to-muted-foreground">
                should review
              </span> <br />
              <span className="text-transparent bg-clip-text bg-linear-to-r from-primary via-orange-500 to-amber-500">
                itself.
              </span>
            </motion.h1>

            <motion.p
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: 0.2 }}
              className="text-base sm:text-lg lg:text-xl text-muted-foreground leading-relaxed max-w-2xl font-normal"
            >
              Ignition deploys deterministic multi-agent graphs to audit architecture, verify business logic, and eliminate vulnerabilities across every pull request before production deployment.
            </motion.p>

            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: 0.3 }}
              className="flex flex-wrap items-center gap-4 pt-4"
            >
              <Link
                href="/login"
                className="group flex items-center gap-2.5 px-8 py-4 bg-primary text-primary-foreground text-sm font-mono uppercase tracking-wider font-bold rounded-full hover:bg-primary/90 transition-all shadow-[0_0_25px_rgba(255,69,0,0.3)] hover:shadow-[0_0_35px_rgba(255,69,0,0.5)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 focus-visible:ring-offset-background"
              >
                Explore Live Dashboard
                <ArrowRight className="w-4 h-4 transition-transform group-hover:translate-x-1" />
              </Link>
              <a
                href="https://github.com"
                target="_blank"
                rel="noreferrer"
                className="flex items-center gap-2.5 px-7 py-4 bg-white/[0.03] border border-white/[0.08] text-foreground text-sm font-mono uppercase tracking-wider font-semibold rounded-full hover:bg-white/[0.06] hover:border-white/[0.14] transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
              >
                <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                  <path
                    fillRule="evenodd"
                    d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.531 1.032 1.531 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z"
                    clipRule="evenodd"
                  />
                </svg>
                View on GitHub
              </a>
            </motion.div>
          </div>

          {/* Right: Technical Engineering Telemetry Panel (Level 1 Subtle Glass) */}
          <div className="lg:col-span-5 w-full">
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 0.6, delay: 0.2 }}
              className="bg-card/60 backdrop-blur-md border border-white/[0.08] rounded-2xl p-6 sm:p-8 shadow-[inset_0_1px_0_0_rgba(255,255,255,0.03)] flex flex-col gap-6"
            >
              {/* Telemetry Header */}
              <div className="flex items-center justify-between pb-4 border-b border-white/[0.06]">
                <div className="flex items-center gap-2 font-mono text-xs text-muted-foreground">
                  <Terminal className="h-4 w-4 text-primary" />
                  <span className="uppercase tracking-wider">Engine Telemetry</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse" />
                  <span className="font-mono text-[10px] text-emerald-400 uppercase tracking-widest">
                    Graph Active
                  </span>
                </div>
              </div>

              {/* Core Metrics Grid */}
              <div className="grid grid-cols-2 gap-4">
                <div className="p-4 rounded-xl bg-background/50 border border-white/[0.04] flex flex-col gap-1">
                  <span className="text-[10px] font-mono uppercase tracking-wider text-muted-foreground">
                    Target ACS
                  </span>
                  <div className="flex items-baseline gap-1.5">
                    <span className="text-3xl font-extrabold font-mono text-foreground tabular-nums">94</span>
                    <span className="text-xs font-mono text-emerald-400 font-semibold">/ 100</span>
                  </div>
                  <span className="text-[10px] text-muted-foreground">High architecture compliance</span>
                </div>

                <div className="p-4 rounded-xl bg-background/50 border border-white/[0.04] flex flex-col gap-1">
                  <span className="text-[10px] font-mono uppercase tracking-wider text-muted-foreground">
                    Active Nodes
                  </span>
                  <div className="flex items-baseline gap-1.5">
                    <span className="text-3xl font-extrabold font-mono text-primary tabular-nums">04</span>
                    <span className="text-xs font-mono text-muted-foreground font-semibold">parallel</span>
                  </div>
                  <span className="text-[10px] text-muted-foreground">Specialist agent runtime</span>
                </div>
              </div>

              {/* Execution Stream Item */}
              <div className="p-4 rounded-xl bg-background/40 border border-white/[0.04] flex flex-col gap-3 font-mono text-xs">
                <div className="flex items-center justify-between text-muted-foreground">
                  <span className="flex items-center gap-1.5">
                    <GitPullRequest className="h-3.5 w-3.5 text-primary" />
                    PR #142: feat/payment-gateway
                  </span>
                  <span className="text-[10px] text-emerald-400 font-semibold">verified</span>
                </div>

                <div className="space-y-1.5 text-[11px]">
                  <div className="flex items-center justify-between text-foreground/90">
                    <span className="flex items-center gap-1.5">
                      <CheckCircle2 className="h-3 w-3 text-emerald-400" />
                      AST Syntax Tree
                    </span>
                    <span className="text-muted-foreground">0.8s</span>
                  </div>
                  <div className="flex items-center justify-between text-foreground/90">
                    <span className="flex items-center gap-1.5">
                      <Cpu className="h-3 w-3 text-primary" />
                      Parallel Logic Assessor
                    </span>
                    <span className="text-muted-foreground">1.4s</span>
                  </div>
                  <div className="flex items-center justify-between text-foreground/90">
                    <span className="flex items-center gap-1.5">
                      <ShieldCheck className="h-3 w-3 text-emerald-400" />
                      Deterministic Verification Gate
                    </span>
                    <span className="text-muted-foreground">0.5s</span>
                  </div>
                </div>
              </div>

              {/* Telemetry Footer Status */}
              <div className="pt-2 flex items-center justify-between text-[11px] font-mono text-muted-foreground">
                <span>False-Positive Filter: Strict</span>
                <span className="text-primary font-bold">Latency: &lt; 42s</span>
              </div>
            </motion.div>
          </div>
        </div>
      </div>
    </section>
  )
}
