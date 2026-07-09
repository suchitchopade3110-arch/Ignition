"use client"

import { motion } from "framer-motion"
import Link from "next/link"
import { ArrowRight } from "lucide-react"

export function CtaSection() {
  return (
    <section className="py-24 relative z-10 overflow-hidden border-t border-border">
      {/* Dynamic Background Beams */}
      <div className="absolute inset-0 bg-secondary/30" />
      <div className="absolute top-0 left-1/2 -translate-x-1/2 w-full max-w-4xl h-[500px] opacity-30 pointer-events-none">
        <div className="absolute inset-0 bg-gradient-to-b from-primary/40 to-transparent blur-3xl rounded-full" />
        <div className="absolute top-1/4 left-1/4 w-[300px] h-[300px] bg-warning/30 blur-[100px] mix-blend-screen rounded-full animate-pulse" />
        <div className="absolute bottom-1/4 right-1/4 w-[250px] h-[250px] bg-primary/30 blur-[100px] mix-blend-screen rounded-full animate-pulse" style={{ animationDelay: '1s' }} />
      </div>

      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 relative z-10 text-center">
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          whileInView={{ opacity: 1, scale: 1 }}
          viewport={{ once: true }}
          transition={{ duration: 0.8, type: "spring" }}
          className="bg-card/50 backdrop-blur-xl border border-border/50 p-12 md:p-20 rounded-[40px] shadow-2xl"
        >
          <motion.h2 
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ delay: 0.2 }}
            className="text-4xl md:text-5xl lg:text-6xl font-bold tracking-tight text-foreground mb-6"
          >
            Ready to transform your code review workflow?
          </motion.h2>
          
          <motion.p 
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ delay: 0.3 }}
            className="text-xl text-muted-foreground mb-12 max-w-2xl mx-auto"
          >
            Join elite engineering teams using Ignition to catch critical bugs, enforce architecture rules, and ship faster.
          </motion.p>
          
          <motion.div 
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ delay: 0.4 }}
            className="flex flex-col sm:flex-row items-center justify-center gap-4"
          >
            <Link 
              href="/login"
              className="w-full sm:w-auto group flex items-center justify-center gap-2 px-8 py-4 bg-primary text-primary-foreground text-lg font-semibold rounded-full hover:bg-primary/90 transition-all shadow-[0_0_20px_rgba(255,69,0,0.3)] hover:shadow-[0_0_30px_rgba(255,69,0,0.6)] hover:-translate-y-0.5"
            >
              Start Free Trial
              <ArrowRight className="w-5 h-5 transition-transform group-hover:translate-x-1" />
            </Link>
            <a 
              href="https://github.com"
              target="_blank"
              rel="noreferrer"
              className="w-full sm:w-auto flex items-center justify-center gap-2 px-8 py-4 bg-background border border-border text-foreground text-lg font-medium rounded-full hover:bg-secondary transition-colors"
            >
              <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                <path fillRule="evenodd" d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.531 1.032 1.531 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z" clipRule="evenodd" />
              </svg>
              View on GitHub
            </a>
          </motion.div>
        </motion.div>
      </div>
    </section>
  )
}
