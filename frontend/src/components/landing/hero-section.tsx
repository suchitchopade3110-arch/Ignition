"use client"

import Link from "next/link"
import { motion } from "framer-motion"
import { HeroProductConsole } from "./hero-product-console"

export function HeroSection() {
  return (
    <section className="relative pt-32 pb-20 md:pt-40 md:pb-28 overflow-hidden">
      <div className="max-w-7xl mx-auto px-6 sm:px-8 lg:px-12">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-12 lg:gap-14 items-center">
          {/* Left Column (~42% width) */}
          <div className="lg:col-span-5 flex flex-col gap-8">
            <motion.div
              initial={{ opacity: 0, y: 15 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.4 }}
              className="flex items-center gap-2 font-mono text-xs text-primary uppercase tracking-widest font-bold"
            >
              <span>01 / CODE INTELLIGENCE</span>
            </motion.div>

            <motion.h1
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: 0.1 }}
              className="text-4xl sm:text-6xl lg:text-6xl xl:text-7xl font-extrabold tracking-tight text-surface-dark-fg leading-[0.98] uppercase font-sans select-none"
            >
              YOUR CODEBASE <br />
              IS ALREADY <br />
              TELLING YOU <br />
              <span className="text-primary">WHAT IS WRONG.</span>
            </motion.h1>

            <motion.p
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: 0.2 }}
              className="text-sm sm:text-base text-surface-dark-muted leading-relaxed max-w-lg"
            >
              Ignition is a multi-agent code review system that understands your repository, analyzes
              every change, and delivers actionable insights with engineering context.
            </motion.p>

            {/* CTAs */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: 0.3 }}
              className="flex flex-wrap items-center gap-6 pt-1"
            >
              <Link
                href="/login"
                className="group flex items-center gap-2.5 px-6 py-3.5 bg-primary hover:bg-primary-hover text-white text-xs font-mono uppercase tracking-wider font-bold rounded-lg transition-all shadow-[0_0_20px_rgba(255,69,0,0.3)] hover:shadow-[0_0_30px_rgba(255,69,0,0.5)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
              >
                <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                  <path
                    fillRule="evenodd"
                    d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.531 1.032 1.531 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z"
                    clipRule="evenodd"
                  />
                </svg>
                Connect GitHub
              </Link>

              <a
                href="#how-it-works"
                className="text-xs font-mono uppercase tracking-wider text-surface-dark-fg hover:text-primary transition-colors flex items-center gap-1.5 focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-primary"
              >
                See how it works ↓
              </a>
            </motion.div>

            {/* Bottom 4 Metrics */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: 0.4 }}
              className="grid grid-cols-4 gap-4 pt-6 border-t border-surface-dark-border font-mono"
            >
              <div>
                <div className="text-[10px] text-surface-dark-muted uppercase tracking-wider mb-1">ACS SCORE</div>
                <div className="text-xl sm:text-2xl font-black text-primary tabular-nums">
                  94<span className="text-xs text-surface-dark-muted font-normal">/100</span>
                </div>
              </div>
              <div>
                <div className="text-[10px] text-surface-dark-muted uppercase tracking-wider mb-1">AGENTS</div>
                <div className="text-xl sm:text-2xl font-black text-surface-dark-fg tabular-nums">04</div>
              </div>
              <div>
                <div className="text-[10px] text-surface-dark-muted uppercase tracking-wider mb-1">FINDINGS</div>
                <div className="text-xl sm:text-2xl font-black text-surface-dark-fg tabular-nums">07</div>
              </div>
              <div>
                <div className="text-[10px] text-surface-dark-muted uppercase tracking-wider mb-1">STATUS</div>
                <div className="text-xs sm:text-sm font-bold text-primary uppercase mt-1.5">
                  COMPLETED
                </div>
              </div>
            </motion.div>
          </div>

          {/* Right Column (~58% width): Real Review Interface */}
          <div className="lg:col-span-7 w-full">
            <motion.div
              initial={{ opacity: 0, scale: 0.96 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 0.6, delay: 0.2 }}
            >
              <HeroProductConsole />
            </motion.div>
          </div>
        </div>
      </div>
    </section>
  )
}
