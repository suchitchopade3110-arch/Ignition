"use client"

import { useState } from "react"
import { Finding } from "@/lib/types"
import { SeverityBadge } from "./severity-badge"
import { ChevronDown, ChevronRight, Copy, FileText, Check } from "lucide-react"

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

  return (
    <div className="rounded-xl border border-border bg-card overflow-hidden transition-all hover:border-border/80">
      {/* Header (Always visible) */}
      <div 
        className="flex flex-col sm:flex-row sm:items-center justify-between p-4 cursor-pointer hover:bg-secondary/30 transition-colors gap-4"
        onClick={() => setExpanded(!expanded)}
      >
        <div className="flex items-start sm:items-center gap-3">
          <button className="mt-0.5 sm:mt-0 text-muted-foreground hover:text-foreground">
            {expanded ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
          </button>
          <SeverityBadge level={finding.severity} />
          <div className="flex flex-col">
            <span className="text-sm font-medium text-foreground">{finding.description}</span>
            <div className="flex items-center gap-2 mt-1">
              <FileText className="h-3 w-3 text-muted-foreground" />
              <span className="text-xs text-muted-foreground font-mono">
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
            <div className="p-4 border-t border-border bg-secondary/10 space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-1">
                  <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Rule Violated</h4>
                  <p className="text-sm text-foreground">{finding.rule}</p>
                </div>
                <div className="space-y-1">
                  <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Recommendation</h4>
                  <p className="text-sm text-foreground">{finding.recommendation}</p>
                </div>
              </div>

              {finding.suggestedFix && (
                <div className="space-y-2 pt-2">
                  <div className="flex items-center justify-between">
                    <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Suggested Fix</h4>
                    <button 
                      onClick={handleCopy}
                      className="flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground transition-colors"
                    >
                      {copied ? <Check className="h-3.5 w-3.5 text-success" /> : <Copy className="h-3.5 w-3.5" />}
                      {copied ? "Copied" : "Copy Fix"}
                    </button>
                  </div>
                  <div className="relative rounded-md bg-secondary/50 p-4 border border-border/50 overflow-x-auto">
                    <pre className="text-sm font-mono text-foreground whitespace-pre-wrap">
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
