"use client"

import { motion } from "framer-motion"
import { Globe, Lock, ArrowUpRight } from "lucide-react"

export function DashboardShowcase() {
  return (
    <section className="py-24 relative z-10 overflow-hidden">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center mb-16">
          <motion.h2 
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            className="text-3xl md:text-4xl font-bold tracking-tight text-foreground mb-4"
          >
            A Command Center for Code Quality
          </motion.h2>
          <motion.p 
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ delay: 0.1 }}
            className="text-lg text-muted-foreground max-w-2xl mx-auto"
          >
            Monitor real-time agent execution, track long-term Architecture Compliance Scores, and manually approve critical PRs from a single, stunning dashboard.
          </motion.p>
        </div>

        <div className="relative mx-auto max-w-5xl">
          {/* Main Browser Frame */}
          <motion.div 
            initial={{ opacity: 0, y: 40 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ type: "spring", stiffness: 100, damping: 20 }}
            className="rounded-xl border border-border bg-card shadow-2xl overflow-hidden relative z-20 group"
          >
            {/* Browser Header */}
            <div className="flex items-center gap-4 px-4 py-3 bg-[#1A1A1A] border-b border-border">
              <div className="flex gap-1.5">
                <div className="w-3 h-3 rounded-full bg-critical/80 group-hover:bg-critical transition-colors" />
                <div className="w-3 h-3 rounded-full bg-warning/80 group-hover:bg-warning transition-colors" />
                <div className="w-3 h-3 rounded-full bg-success/80 group-hover:bg-success transition-colors" />
              </div>
              <div className="flex-1 flex justify-center">
                <div className="flex items-center gap-2 px-3 py-1.5 bg-[#0F0F0F] rounded-md border border-border/50 text-xs text-muted-foreground min-w-[300px] justify-center">
                  <Lock className="w-3 h-3" />
                  app.ignition.dev/dashboard
                </div>
              </div>
              <div className="w-[52px]" /> {/* Spacer for balance */}
            </div>

            {/* Dashboard Mock Content */}
            <div className="bg-background p-6 h-[500px] relative">
              {/* Sidebar Mock */}
              <div className="absolute left-0 top-0 bottom-0 w-48 border-r border-border bg-card p-4 hidden md:block">
                <div className="h-6 w-24 bg-primary/20 rounded mb-8" />
                <div className="space-y-3">
                  <div className="h-4 w-full bg-secondary rounded" />
                  <div className="h-4 w-3/4 bg-secondary rounded" />
                  <div className="h-4 w-5/6 bg-secondary rounded" />
                  <div className="h-4 w-2/3 bg-secondary rounded" />
                </div>
              </div>

              {/* Main Area Mock */}
              <div className="md:ml-48 p-4">
                <div className="flex justify-between items-center mb-6">
                  <div className="h-6 w-32 bg-secondary rounded" />
                  <div className="h-8 w-24 bg-primary/20 rounded-full" />
                </div>

                <div className="grid grid-cols-3 gap-4 mb-6">
                  <div className="h-24 bg-card border border-border rounded-lg p-4">
                    <div className="h-3 w-16 bg-secondary rounded mb-4" />
                    <div className="h-8 w-12 bg-foreground/10 rounded" />
                  </div>
                  <div className="h-24 bg-card border border-border rounded-lg p-4">
                    <div className="h-3 w-16 bg-secondary rounded mb-4" />
                    <div className="h-8 w-12 bg-foreground/10 rounded" />
                  </div>
                  <div className="h-24 bg-card border border-border rounded-lg p-4">
                    <div className="h-3 w-16 bg-secondary rounded mb-4" />
                    <div className="h-8 w-12 bg-foreground/10 rounded" />
                  </div>
                </div>

                <div className="h-48 bg-card border border-border rounded-lg p-4">
                  <div className="h-3 w-24 bg-secondary rounded mb-6" />
                  <div className="space-y-3">
                    <div className="h-3 w-full bg-secondary/50 rounded" />
                    <div className="h-3 w-full bg-secondary/50 rounded" />
                    <div className="h-3 w-3/4 bg-secondary/50 rounded" />
                    <div className="h-3 w-full bg-secondary/50 rounded" />
                  </div>
                </div>
              </div>

              {/* Hover Overlay */}
              <div className="absolute inset-0 bg-background/80 backdrop-blur-sm opacity-0 group-hover:opacity-100 transition-opacity duration-300 flex items-center justify-center">
                <motion.div 
                  initial={{ scale: 0.9, opacity: 0 }}
                  whileHover={{ scale: 1.05 }}
                  className="bg-card border border-border p-6 rounded-xl shadow-2xl text-center max-w-sm"
                >
                  <Globe className="w-8 h-8 text-primary mx-auto mb-4" />
                  <h4 className="text-lg font-bold text-foreground mb-2">Explore the Platform</h4>
                  <p className="text-sm text-muted-foreground mb-4">Log in to view the live dashboard and experience the real-time AI capabilities.</p>
                  <a href="/login" className="inline-flex items-center gap-2 text-primary font-medium hover:text-primary/80">
                    Go to Dashboard <ArrowUpRight className="w-4 h-4" />
                  </a>
                </motion.div>
              </div>
            </div>
          </motion.div>

          {/* Decorative Elements */}
          <div className="absolute -left-12 top-1/4 w-32 h-32 bg-primary/20 rounded-full blur-[40px] pointer-events-none -z-10" />
          <div className="absolute -right-12 bottom-1/4 w-40 h-40 bg-warning/10 rounded-full blur-[60px] pointer-events-none -z-10" />
        </div>
      </div>
    </section>
  )
}
