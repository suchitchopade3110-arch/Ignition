"use client"

import { motion } from "framer-motion"
import { Server, Database, Code, Globe, Layout, CheckCircle, Smartphone } from "lucide-react"

const technologies = [
  { name: "FastAPI", icon: Server },
  { name: "LangGraph", icon: Globe },
  { name: "Next.js", icon: Layout },
  { name: "Supabase", icon: Database },
  { name: "Tailwind CSS", icon: Smartphone },
  { name: "TypeScript", icon: Code },
  { name: "GitHub App", icon: CheckCircle },
]

export function TechStack() {
  return (
    <section id="technology" className="py-24 relative z-10 border-t border-border/50 bg-secondary/10">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center mb-16">
          <motion.h2 
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            className="text-3xl md:text-4xl font-bold tracking-tight text-foreground mb-4"
          >
            Built on a Modern Stack
          </motion.h2>
          <motion.p 
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ delay: 0.1 }}
            className="text-lg text-muted-foreground max-w-2xl mx-auto"
          >
            Ignition leverages the latest frameworks to ensure blazing fast performance, secure webhook handling, and real-time streaming capabilities.
          </motion.p>
        </div>

        <div className="flex flex-wrap justify-center gap-6">
          {technologies.map((tech, i) => (
            <motion.div
              key={tech.name}
              initial={{ opacity: 0, scale: 0.9 }}
              whileInView={{ opacity: 1, scale: 1 }}
              viewport={{ once: true }}
              transition={{ delay: i * 0.1 }}
              whileHover={{ y: -5, scale: 1.05 }}
              className="flex items-center gap-3 px-6 py-4 bg-card border border-border rounded-2xl shadow-sm hover:shadow-[0_0_15px_rgba(255,69,0,0.15)] hover:border-primary/30 transition-all cursor-default"
            >
              <tech.icon className="w-6 h-6 text-primary" />
              <span className="font-semibold text-foreground">{tech.name}</span>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  )
}
