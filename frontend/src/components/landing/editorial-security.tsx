"use client"

import { motion } from "framer-motion"
import { ShieldCheck, Lock, FileCheck, KeyRound } from "lucide-react"

const securityPillars = [
  {
    icon: Lock,
    title: "Ephemeral Repository Isolation",
    description:
      "Customer source code is parsed in memory in isolated ephemeral runtime environments and immediately wiped post-analysis. Zero persistent code storage on disk.",
  },
  {
    icon: KeyRound,
    title: "HMAC Webhook Verification",
    description:
      "All GitHub App webhooks and pull request payloads are verified cryptographically via SHA-256 HMAC signatures before reaching the execution orchestrator.",
  },
  {
    icon: FileCheck,
    title: "Immutable Review Ledger",
    description:
      "Every review finding, critic validation, and Human-in-the-Loop decision is logged to an immutable audit trail for compliance and regression analysis.",
  },
  {
    icon: ShieldCheck,
    title: "Deterministic Rule Enforcement",
    description:
      "Hard security boundaries ensure that untrusted third-party code in pull requests cannot trigger arbitrary network requests or unauthorized API calls.",
  },
]

export function EditorialSecurity() {
  return (
    <section id="security" className="py-32 md:py-44 relative">
      <div className="max-w-7xl mx-auto px-6 sm:px-8 lg:px-12">
        {/* Section Header */}
        <div className="flex flex-col gap-4 mb-20 md:mb-28 max-w-3xl">
          <span className="text-xs font-mono font-bold tracking-widest text-primary uppercase">
            07 / Security Architecture
          </span>
          <h2 className="text-4xl sm:text-5xl lg:text-6xl font-extrabold tracking-tight text-foreground uppercase font-sans">
            Built on zero-trust <br />
            <span className="text-muted-foreground">engineering principles.</span>
          </h2>
          <p className="text-base sm:text-lg text-muted-foreground leading-relaxed pt-2">
            Enterprise-ready code review requires verifiable isolation, cryptographic integrity, and zero code retention.
          </p>
        </div>

        {/* 2x2 Grid of Concrete Security Pillars */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-8 lg:gap-10">
          {securityPillars.map((pillar, idx) => {
            const Icon = pillar.icon
            return (
              <motion.div
                key={pillar.title}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.4, delay: idx * 0.1 }}
                className="bg-card/60 backdrop-blur-md border border-white/[0.08] rounded-2xl p-8 shadow-[inset_0_1px_0_0_rgba(255,255,255,0.03)] flex flex-col gap-5"
              >
                <div className="p-3 rounded-xl bg-white/[0.03] border border-white/[0.08] w-fit text-primary">
                  <Icon className="h-6 w-6" />
                </div>
                <h3 className="text-xl font-bold text-foreground uppercase font-sans">
                  {pillar.title}
                </h3>
                <p className="text-sm sm:text-base text-muted-foreground leading-relaxed">
                  {pillar.description}
                </p>
              </motion.div>
            )
          })}
        </div>
      </div>
    </section>
  )
}
