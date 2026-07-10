"use client"

import { useState } from "react"
import { Finding } from "@/lib/types"
import { SeverityBadge } from "./severity-badge"
import { ChevronDown, ChevronRight, Copy, FileText, Check } from "lucide-react"
import { cn } from "@/lib/utils"

import { motion, AnimatePresence } from "framer-motion"

export function FindingCard({ finding }: { finding: Finding }) {
  const [expanded, setExpanded] = useState(false)
  const [copied, setCopied] = useState(false)

  const handleCopy = (e: React.MouseEvent) => {
    e.stopPropagation()
    if (finding.suggestedFix) {
      navigator.clipboard.writeText(finding.suggestedFix.replace(/```[a-z]*\n/g, '').replace(/```/g, ''))
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    }
  }

  // Choose border color based on severity
  const severityBorderClasses: Record<string, string> = {
    none: "hover:border-[#4A5056]/50",
    low: "hover:border-info/40",
    medium: "hover:border-warning/40",
    high: "hover:border-danger/40",
    critical: "hover:border-critical/40",
  }
  const borderHoverClass = severityBorderClasses[finding.severity] || "hover:border-[#22262B]/80"

  return (
    <div className={cn(
      "rounded-xl border border-[#22262B] bg-[#14171A] overflow-hidden transition-all duration-300 shadow-md shadow-black/10",
      borderHoverClass,
      expanded && "shadow-lg shadow-black/25 border-[#22262B]/80"
    )}>
      {/* Header (Always visible) */}
      <div 
        className="flex flex-col sm:flex-row sm:items-center justify-between p-4 cursor-pointer hover:bg-[#1C1F22]/50 transition-colors gap-4"
        onClick={() => setExpanded(!expanded)}
      >
        <div className="flex items-start sm:items-center gap-3">
          <button className="mt-0.5 sm:mt-0 text-muted-foreground hover:text-foreground transition-colors shrink-0">
            {expanded ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
          </button>
          <SeverityBadge level={finding.severity} className="shrink-0" />
          <div className="flex flex-col min-w-0">
            <span className="text-sm font-semibold text-foreground leading-snug">{finding.description}</span>
            <div className="flex items-center gap-2 mt-1.5">
              <FileText className="h-3.5 w-3.5 text-muted-foreground shrink-0" />
              <span className="text-xs text-muted-foreground font-mono truncate">
                {finding.file}{finding.line ? `:${finding.line}` : ''}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Expanded Content */}
      <AnimatePresence>
        {expanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="overflow-hidden"
          >
            <div className="p-4 border-t border-[#22262B] bg-[#0B0D0F]/40 space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-1 bg-[#14171A] p-3 rounded-lg border border-[#22262B]/50">
                  <h4 className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider">Rule Violated</h4>
                  <p className="text-xs text-foreground font-mono">{finding.rule}</p>
                </div>
                <div className="space-y-1 bg-[#14171A] p-3 rounded-lg border border-[#22262B]/50">
                  <h4 className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider">Recommendation</h4>
                  <p className="text-xs text-foreground">{finding.recommendation}</p>
                </div>
              </div>

              {finding.suggestedFix && (
                <div className="space-y-2 pt-2">
                  <div className="flex items-center justify-between">
                    <h4 className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider">Suggested Fix</h4>
                    <button 
                      onClick={handleCopy}
                      className="flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground transition-colors font-mono"
                    >
                      {copied ? <Check className="h-3.5 w-3.5 text-success" /> : <Copy className="h-3.5 w-3.5" />}
                      {copied ? "Copied" : "Copy Fix"}
                    </button>
                  </div>
                  <div className="relative rounded-lg bg-[#0B0D0F] p-4 border border-[#22262B] overflow-x-auto max-h-96">
                    <pre className="text-xs font-mono text-foreground whitespace-pre-wrap leading-relaxed">
                      {/* Very basic markdown code block stripping for display */}
                      {finding.suggestedFix.replace(/```[a-z]*\n/g, '').replace(/```/g, '')}
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
