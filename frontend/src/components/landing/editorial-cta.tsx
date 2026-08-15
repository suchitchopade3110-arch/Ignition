"use client"

import Link from "next/link"
import { motion } from "framer-motion"
import { ArrowRight } from "lucide-react"

export function EditorialCta() {
  return (
    <section className="py-36 md:py-48 relative overflow-hidden">
      <div className="max-w-7xl mx-auto px-6 sm:px-8 lg:px-12 text-center">
        <div className="flex flex-col items-center gap-8 max-w-4xl mx-auto">
          <motion.span
            initial={{ opacity: 0, y: 15 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            className="text-xs font-mono font-bold tracking-widest text-primary uppercase"
          >
            08 / Begin Review
          </motion.span>

          <motion.h2
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5, delay: 0.1 }}
            className="text-5xl sm:text-7xl lg:text-8xl font-black tracking-tight text-foreground uppercase font-sans leading-[0.95] select-none"
          >
            Ready to review <br />
            <span className="text-transparent bg-clip-text bg-linear-to-r from-primary via-orange-500 to-amber-500">
              differently?
            </span>
          </motion.h2>

          <motion.p
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5, delay: 0.2 }}
            className="text-base sm:text-xl text-muted-foreground leading-relaxed max-w-2xl"
          >
            Connect your repository. Let Ignition&apos;s multi-agent graph start autonomous, deterministic code analysis today.
          </motion.p>

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5, delay: 0.3 }}
            className="flex flex-wrap items-center justify-center gap-4 pt-4"
          >
            <Link
              href="/login"
              className="group flex items-center gap-2.5 px-9 py-4 bg-primary text-primary-foreground text-sm font-mono uppercase tracking-wider font-bold rounded-full hover:bg-primary/90 transition-all shadow-[0_0_30px_rgba(255,69,0,0.35)] hover:shadow-[0_0_40px_rgba(255,69,0,0.5)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 focus-visible:ring-offset-background"
            >
              Get Started with GitHub
              <ArrowRight className="w-4 h-4 transition-transform group-hover:translate-x-1" />
            </Link>
            <Link
              href="/dashboard"
              className="flex items-center gap-2 px-8 py-4 bg-white/[0.03] border border-white/[0.08] text-foreground text-sm font-mono uppercase tracking-wider font-semibold rounded-full hover:bg-white/[0.06] hover:border-white/[0.14] transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
            >
              View Live Demo
            </Link>
          </motion.div>
        </div>
      </div>
    </section>
  )
}
