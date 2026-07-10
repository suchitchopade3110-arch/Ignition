"use client"

import Link from "next/link"
import Image from "next/image"
import { motion } from "framer-motion"
import { ArrowRight } from "lucide-react"
import { PipelineDiagram } from "@/components/landing/pipeline-diagram"
import { GithubSuggestionCatch } from "@/components/github-suggestion-catch"

export default function LandingPage() {
  const containerVariants = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: {
        staggerChildren: 0.1,
        delayChildren: 0.1
      }
    }
  }

  const itemVariants = {
    hidden: { opacity: 0, y: 20 },
    visible: { 
      opacity: 1, 
      y: 0, 
      transition: { type: "spring" as const, stiffness: 200, damping: 20 } 
    }
  }

  return (
    <div className="min-h-screen bg-background bg-ignition-pattern text-foreground selection:bg-primary/30 flex flex-col justify-between">
      {/* Navigation Header */}
      <header className="h-20 flex items-center justify-between px-6 md:px-12 border-b border-border bg-background/50 backdrop-blur-md sticky top-0 z-50">
        <Link href="/" className="flex items-center gap-3">
          <div className="relative h-8 w-8">
            <Image src="/logo.svg" alt="Ignition Logo" fill className="object-contain" />
          </div>
          <span className="text-xl font-bold tracking-tight text-foreground font-mono">ignition</span>
        </Link>
        <Link 
          href="/login" 
          className="flex items-center gap-1.5 px-5 py-2 rounded-full border border-border bg-secondary/50 hover:bg-secondary text-sm font-semibold transition-colors"
        >
          sign in
        </Link>
      </header>

      {/* Main Content */}
      <main className="flex-1 max-w-6xl mx-auto w-full px-6 md:px-12 py-16 flex flex-col gap-32">
        {/* Section 1: Hero */}
        <motion.section 
          variants={containerVariants}
          initial="hidden"
          animate="visible"
          className="flex flex-col items-center text-center max-w-3xl mx-auto gap-8 pt-8"
        >
          <motion.h1 
            variants={itemVariants}
            className="text-4xl sm:text-6xl font-extrabold tracking-tight leading-[1.05] text-foreground lowercase"
          >
            autonomous multi-agent <br />
            <span className="text-transparent bg-clip-text bg-linear-to-r from-primary to-orange-500">
              ai code reviews
            </span>
          </motion.h1>

          <motion.p 
            variants={itemVariants}
            className="text-base sm:text-lg text-muted-foreground leading-relaxed lowercase"
          >
            ignition runs deep architecture, logic, and security audits on every pull request before your code hits production. verified findings, not guesses.
          </motion.p>

          <motion.div 
            variants={itemVariants}
            className="flex flex-wrap items-center justify-center gap-4 pt-4"
          >
            <Link 
              href="/login"
              className="group flex items-center gap-2 px-8 py-3.5 bg-primary text-primary-foreground text-sm font-bold rounded-full hover:bg-primary/90 transition-all shadow-[0_0_20px_rgba(255,69,0,0.2)] hover:shadow-[0_0_25px_rgba(255,69,0,0.4)]"
            >
              explore live dashboard
              <ArrowRight className="w-4 h-4 transition-transform group-hover:translate-x-1" />
            </Link>
            <a 
              href="https://github.com"
              target="_blank"
              rel="noreferrer"
              className="flex items-center gap-2 px-6 py-3.5 bg-secondary/50 border border-border/80 text-foreground text-sm font-semibold rounded-full hover:bg-secondary transition-colors"
            >
              <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                <path fillRule="evenodd" d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.531 1.032 1.531 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z" clipRule="evenodd" />
              </svg>
              view on github
            </a>
          </motion.div>
        </motion.section>

        {/* Section 2: Interactive Pipeline */}
        <section className="flex flex-col gap-8">
          <div className="flex flex-col gap-2 max-w-xl">
            <span className="text-xs uppercase font-mono font-bold tracking-widest text-primary">
              how it works
            </span>
            <h2 className="text-2xl sm:text-3xl font-bold tracking-tight text-foreground lowercase">
              multi-agent orchestration pipeline
            </h2>
            <p className="text-sm sm:text-base text-muted-foreground lowercase">
              hover over or tap each stage to inspect what happens during an active review.
            </p>
          </div>
          <PipelineDiagram />
        </section>

        {/* Section 3: Proof Point */}
        <section className="grid grid-cols-1 lg:grid-cols-12 gap-12 items-center">
          <div className="lg:col-span-5 flex flex-col gap-4">
            <span className="text-xs uppercase font-mono font-bold tracking-widest text-primary">
              proof of craft
            </span>
            <h2 className="text-2xl sm:text-3xl font-bold tracking-tight text-foreground lowercase">
              deterministic findings, precise fixes
            </h2>
            <p className="text-sm sm:text-base text-muted-foreground leading-relaxed lowercase">
              we do not write vague summaries. ignition identifies precise errors—such as N+1 loops, logic gaps, or security flaws—and proposes exact inline code replacements directly into github.
            </p>
          </div>
          <div className="lg:col-span-7">
            <GithubSuggestionCatch />
          </div>
        </section>

        {/* Section 4: Core Principles */}
        <section className="flex flex-col gap-10">
          <div className="flex flex-col gap-2 max-w-xl">
            <span className="text-xs uppercase font-mono font-bold tracking-widest text-primary">
              engineering core
            </span>
            <h2 className="text-2xl sm:text-3xl font-bold tracking-tight text-foreground lowercase">
              our core review principles
            </h2>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="p-6 rounded-2xl bg-card/25 border border-border/80 flex flex-col gap-2">
              <h3 className="text-base font-bold text-foreground lowercase">deterministic before semantic</h3>
              <p className="text-sm text-muted-foreground leading-relaxed lowercase">
                we prioritize static analysis patterns and explicit abstract syntax trees (ASTs) before leveraging LLM generation to eliminate hallucinations entirely.
              </p>
            </div>
            <div className="p-6 rounded-2xl bg-card/25 border border-border/80 flex flex-col gap-2">
              <h3 className="text-base font-bold text-foreground lowercase">verification before trust</h3>
              <p className="text-sm text-muted-foreground leading-relaxed lowercase">
                every potential issue flagged by our specialist nodes goes through a secondary verification passes to filter out false positives before display.
              </p>
            </div>
            <div className="p-6 rounded-2xl bg-card/25 border border-border/80 flex flex-col gap-2">
              <h3 className="text-base font-bold text-foreground lowercase">bounded self-correction</h3>
              <p className="text-sm text-muted-foreground leading-relaxed lowercase">
                if the critic detects a hallucinated finding, the graph can loop back for more context, but only up to a hard retry cap — preventing runaway cost or infinite cycles.
              </p>
            </div>
          </div>
        </section>
      </main>

      {/* Section 5: Footer */}
      <footer className="border-t border-border bg-card/30 py-8 px-6 md:px-12 mt-16">
        <div className="max-w-6xl mx-auto flex flex-col md:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="relative h-6 w-6">
              <Image src="/logo.svg" alt="Ignition Logo" fill className="object-contain" />
            </div>
            <span className="text-sm font-semibold tracking-tight text-foreground font-mono">ignition</span>
          </div>
          <p className="text-xs text-muted-foreground">
            &copy; {new Date().getFullYear()} ignition. all rights reserved.
          </p>
          <div className="flex items-center gap-6 text-xs text-muted-foreground">
            <a href="https://github.com" target="_blank" rel="noreferrer" className="hover:text-foreground transition-colors lowercase">
              github
            </a>
            <a href="mailto:support@ignition.ai" className="hover:text-foreground transition-colors lowercase">
              contact
            </a>
          </div>
        </div>
      </footer>
    </div>
  )
}
