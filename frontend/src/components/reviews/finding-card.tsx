"use client"

import { useState } from "react"
import { Finding } from "@/types"
import { SeverityBadge } from "@/components/ui/severity-badge"
import { ChevronDown, ChevronRight, Copy, FileText, Check } from "lucide-react"
import { cn } from "@/lib/utils"
import { motion, AnimatePresence, useReducedMotion } from "framer-motion"

export function FindingCard({ finding }: { finding: Finding }) {
  const [expanded, setExpanded] = useState(false)
  const [copied, setCopied] = useState(false)
  const prefersReducedMotion = useReducedMotion()

  const handleCopy = (e: React.MouseEvent) => {
    e.stopPropagation()
    if (finding.suggestedFix) {
      navigator.clipboard.writeText(finding.suggestedFix.replace(/```[a-z]*\n/g, "").replace(/```/g, ""))
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    }
  }

  // Choose border color based on severity
  const severityBorderClasses: Record<string, string> = {
    none: "hover:border-border",
    low: "hover:border-info/40",
    medium: "hover:border-warning/40",
    high: "hover:border-destructive/40",
    critical: "hover:border-critical/40",
  }
  const borderHoverClass = severityBorderClasses[finding.severity] || "hover:border-border"

  return (
    <div
      className={cn(
        "rounded-xl border border-white/[0.08] bg-card overflow-hidden transition-colors duration-200 shadow-[inset_0_1px_0_0_rgba(255,255,255,0.03)]",
        borderHoverClass,
        expanded && "border-white/[0.12]"
      )}
    >
      {/* Header (Always visible) */}
      <div
        className="flex flex-col sm:flex-row sm:items-center justify-between p-4 cursor-pointer hover:bg-white/[0.02] transition-colors gap-4"
        onClick={() => setExpanded(!expanded)}
      >
        <div className="flex items-start sm:items-center gap-3">
          <button
            type="button"
            aria-label={expanded ? "Collapse finding" : "Expand finding"}
            className="mt-0.5 sm:mt-0 text-muted-foreground hover:text-foreground transition-colors shrink-0"
          >
            {expanded ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
          </button>
          <SeverityBadge level={finding.severity} className="shrink-0" />
          <div className="flex flex-col min-w-0">
            <span className="text-sm font-semibold text-foreground leading-snug">{finding.description}</span>
            <div className="flex items-center gap-2 mt-1.5">
              <FileText className="h-3.5 w-3.5 text-muted-foreground shrink-0" />
              <span className="text-xs text-muted-foreground font-mono truncate">
                {finding.file}{finding.line ? `:${finding.line}` : ""}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Expanded Content */}
      <AnimatePresence>
        {expanded && (
          <motion.div
            initial={prefersReducedMotion ? { opacity: 0 } : { height: 0, opacity: 0 }}
            animate={prefersReducedMotion ? { opacity: 1 } : { height: "auto", opacity: 1 }}
            exit={prefersReducedMotion ? { opacity: 0 } : { height: 0, opacity: 0 }}
            className="overflow-hidden"
          >
            <div className="p-4 border-t border-white/[0.06] bg-black/30 space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-1 bg-card p-3 rounded-lg border border-white/[0.06]">
                  <h4 className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider">Rule Violated</h4>
                  <p className="text-xs text-foreground font-mono">{finding.rule}</p>
                </div>
                <div className="space-y-1 bg-card p-3 rounded-lg border border-white/[0.06]">
                  <h4 className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider">Recommendation</h4>
                  <p className="text-xs text-foreground">{finding.recommendation}</p>
                </div>
              </div>

              {finding.suggestedFix && (
                <div className="space-y-2 pt-2">
                  <div className="flex items-center justify-between">
                    <h4 className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider">Suggested Fix</h4>
                    <button
                      type="button"
                      onClick={handleCopy}
                      aria-label="Copy suggested fix to clipboard"
                      className="flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground transition-colors font-mono p-1 rounded focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
                    >
                      {copied ? <Check className="h-3.5 w-3.5 text-success" /> : <Copy className="h-3.5 w-3.5" />}
                      {copied ? "Copied" : "Copy Fix"}
                    </button>
                  </div>
                  {/* Level 0 Flat Code Box - Crystal Clear Syntax */}
                  <div className="relative rounded-lg bg-background p-4 border border-white/[0.08] overflow-x-auto max-h-96">
                    <pre className="text-xs font-mono text-foreground whitespace-pre-wrap leading-relaxed">
                      {finding.suggestedFix.replace(/```[a-z]*\n/g, "").replace(/```/g, "")}
                    </pre>
                  </div>
                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
