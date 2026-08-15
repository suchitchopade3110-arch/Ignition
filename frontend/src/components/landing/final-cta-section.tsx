"use client"

import Link from "next/link"
import { motion } from "framer-motion"
import { ArrowRight } from "lucide-react"
import { NetworkGlobe } from "./network-globe"

export function FinalCtaSection() {
  return (
    <section className="py-24 md:py-32 relative bg-surface-dark border-t border-surface-dark-border overflow-hidden">
      <div className="max-w-7xl mx-auto px-6 sm:px-8 lg:px-12 relative z-10">
        {/* Section Category Header */}
        <div className="mb-12 md:mb-16">
          <span className="font-mono text-xs text-primary uppercase tracking-widest font-bold">
            05 / GET STARTED
          </span>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-10 lg:gap-14 items-center">
          {/* Left Column (~48% width): Headline, Copy, & CTA */}
          <div className="lg:col-span-6 flex flex-col justify-between gap-8 lg:pr-8 lg:border-r lg:border-surface-dark-border/80">
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5 }}
            >
              <h2 className="text-4xl sm:text-5xl xl:text-6xl font-black text-surface-dark-fg uppercase leading-[1.0] tracking-tight font-sans">
                READY TO REVIEW <br />
                DIFFERENTLY?
              </h2>
            </motion.div>

            <motion.div
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5, delay: 0.15 }}
              className="flex flex-col gap-6 max-w-md"
            >
              <p className="text-sm sm:text-base text-surface-dark-muted leading-relaxed font-sans">
                Connect your GitHub repository and let Ignition start the analysis.
              </p>

              <div>
                <Link
                  href="/login"
                  className="group inline-flex items-center gap-2.5 px-6 py-3.5 bg-primary hover:bg-primary-hover text-white text-xs font-mono uppercase tracking-wider font-bold rounded-lg transition-all shadow-[0_0_20px_rgba(255,69,0,0.35)] hover:shadow-[0_0_30px_rgba(255,69,0,0.55)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
                >
                  <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                    <path
                      fillRule="evenodd"
                      d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.531 1.032 1.531 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z"
                      clipRule="evenodd"
                    />
                  </svg>
                  <span>Connect GitHub</span>
                  <ArrowRight className="w-3.5 h-3.5 transition-transform group-hover:translate-x-0.5" />
                </Link>
              </div>
            </motion.div>
          </div>

          {/* Right Column (~52% width): Large Cinematic Network Globe */}
          <motion.div
            initial={{ opacity: 0, scale: 0.92 }}
            whileInView={{ opacity: 1, scale: 1 }}
            viewport={{ once: true }}
            transition={{ duration: 0.7, delay: 0.2 }}
            className="lg:col-span-6 flex items-center justify-center w-full h-[260px] sm:h-[360px] lg:h-[500px] xl:h-[540px] max-w-[280px] sm:max-w-[380px] lg:max-w-none mx-auto lg:mx-0 relative overflow-visible"
          >
            <NetworkGlobe className="w-full h-full" />
          </motion.div>
        </div>
      </div>
    </section>
  )
}
