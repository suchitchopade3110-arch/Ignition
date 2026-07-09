"use client"

import { useState } from "react"
import { motion, AnimatePresence } from "framer-motion"
import { Network, Zap, Shield, Brain, ArrowRight, Code2 } from "lucide-react"

const architectureNodes = [
  {
    id: "context",
    title: "Context Fetcher",
    icon: Network,
    purpose: "Extracts deep repository context beyond the diff, including related files and architectural diagrams.",
    input: "GitHub Webhook (PR Payload)",
    output: "Enriched Context Object",
    tech: "FastAPI, GitHub GraphQL API"
  },
  {
    id: "gate",
    title: "Hard Rule Gate",
    icon: Zap,
    purpose: "Instantly rejects PRs violating non-negotiable enterprise rules (e.g., exposed secrets, forbidden APIs).",
    input: "Enriched Context",
    output: "Pass/Fail Decision",
    tech: "AST Parsers, Regex Engine"
  },
  {
    id: "structural",
    title: "Structural Agent",
    icon: Code2,
    purpose: "Validates architecture compliance, design patterns, and SOLID principles.",
    input: "AST & PR Diff",
    output: "Structural Findings",
    tech: "LangChain, Claude 3.5 Sonnet"
  },
  {
    id: "logic",
    title: "Logic Assessor",
    icon: Brain,
    purpose: "Identifies edge cases, race conditions, and chaotic state management.",
    input: "Execution Flow graph",
    output: "Logic Vulnerabilities",
    tech: "LangGraph, GPT-4o"
  },
  {
    id: "security",
    title: "Security Auditor",
    icon: Shield,
    purpose: "Deep scans for OWASP Top 10 vulnerabilities and supply chain risks in package changes.",
    input: "Dependencies & Code",
    output: "Security Threat Report",
    tech: "Semgrep bindings, LLM Heuristics"
  }
]

export function ArchitectureSection() {
  const [activeNode, setActiveNode] = useState(architectureNodes[0].id)

  return (
    <section id="architecture" className="py-24 relative z-10 border-t border-border/50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center mb-16">
          <motion.h2 
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            className="text-3xl md:text-4xl font-bold tracking-tight text-foreground mb-4"
          >
            Deterministic Multi-Agent Architecture
          </motion.h2>
          <motion.p 
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ delay: 0.1 }}
            className="text-lg text-muted-foreground max-w-2xl mx-auto"
          >
            Explore the pipeline. Ignition doesn&apos;t rely on a single monolithic LLM. It routes your code through specialized expert agents working in parallel.
          </motion.p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 lg:gap-12 items-start">
          
          {/* Left Side: Interactive Workflow Map */}
          <div className="lg:col-span-5 space-y-4">
            {architectureNodes.map((node, i) => {
              const isActive = activeNode === node.id
              return (
                <motion.button
                  key={node.id}
                  initial={{ opacity: 0, x: -20 }}
                  whileInView={{ opacity: 1, x: 0 }}
                  viewport={{ once: true }}
                  transition={{ delay: i * 0.1 }}
                  onClick={() => setActiveNode(node.id)}
                  className={`w-full text-left p-4 rounded-xl border transition-all duration-300 flex items-center gap-4 group ${
                    isActive 
                      ? "bg-primary/10 border-primary shadow-[0_0_20px_rgba(255,69,0,0.15)]" 
                      : "bg-card border-border hover:border-primary/50 hover:bg-secondary/50"
                  }`}
                >
                  <div className={`p-2 rounded-lg transition-colors ${isActive ? "bg-primary text-primary-foreground" : "bg-secondary text-muted-foreground group-hover:text-foreground"}`}>
                    <node.icon className="w-5 h-5" />
                  </div>
                  <span className={`font-semibold text-base transition-colors ${isActive ? "text-foreground" : "text-muted-foreground group-hover:text-foreground"}`}>
                    {node.title}
                  </span>
                  {isActive && (
                    <motion.div layoutId="active-indicator" className="ml-auto">
                      <ArrowRight className="w-5 h-5 text-primary" />
                    </motion.div>
                  )}
                </motion.button>
              )
            })}
          </div>

          {/* Right Side: Node Details */}
          <div className="lg:col-span-7 h-full">
            <div className="bg-card border border-border rounded-2xl p-8 lg:p-12 shadow-xl h-full relative overflow-hidden">
              {/* Background accent */}
              <div className="absolute -top-32 -right-32 w-64 h-64 bg-primary/5 rounded-full blur-[80px] pointer-events-none" />
              
              <AnimatePresence mode="wait">
                {architectureNodes.map((node) => node.id === activeNode && (
                  <motion.div
                    key={node.id}
                    initial={{ opacity: 0, y: 10, filter: "blur(4px)" }}
                    animate={{ opacity: 1, y: 0, filter: "blur(0px)" }}
                    exit={{ opacity: 0, y: -10, filter: "blur(4px)" }}
                    transition={{ duration: 0.3 }}
                    className="h-full flex flex-col"
                  >
                    <div className="flex items-center gap-4 mb-8">
                      <div className="p-3 bg-primary/20 text-primary rounded-xl border border-primary/30">
                        <node.icon className="w-8 h-8" />
                      </div>
                      <h3 className="text-3xl font-bold text-foreground">{node.title}</h3>
                    </div>

                    <p className="text-lg text-muted-foreground mb-10 leading-relaxed">
                      {node.purpose}
                    </p>

                    <div className="space-y-6 mt-auto">
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                        <div className="p-5 rounded-xl bg-secondary/50 border border-border/50">
                          <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2">Input</p>
                          <p className="text-sm font-medium text-foreground">{node.input}</p>
                        </div>
                        <div className="p-5 rounded-xl bg-secondary/50 border border-border/50">
                          <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2">Output</p>
                          <p className="text-sm font-medium text-foreground">{node.output}</p>
                        </div>
                      </div>
                      
                      <div className="p-5 rounded-xl bg-primary/5 border border-primary/20">
                        <p className="text-xs font-semibold text-primary uppercase tracking-wider mb-2">Technology Stack</p>
                        <p className="text-sm font-medium text-foreground">{node.tech}</p>
                      </div>
                    </div>
                  </motion.div>
                ))}
              </AnimatePresence>
            </div>
          </div>

        </div>
      </div>
    </section>
  )
}
