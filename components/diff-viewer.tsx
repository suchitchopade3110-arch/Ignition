"use client"

import { useState } from "react"
import { ChevronDown, ChevronRight, FileCode2 } from "lucide-react"
import { cn } from "@/lib/utils"

interface DiffViewerProps {
  file: string
  content: string
  additions: number
  deletions: number
  defaultExpanded?: boolean
}

export function DiffViewer({ file, content, additions, deletions, defaultExpanded = true }: DiffViewerProps) {
  const [isExpanded, setIsExpanded] = useState(defaultExpanded)

  const lines = content.split("\n")

  return (
    <div className="rounded-xl border border-border bg-card overflow-hidden">
      {/* Header */}
      <div 
        className="flex items-center justify-between px-4 py-3 bg-secondary/30 border-b border-border cursor-pointer hover:bg-secondary/50 transition-colors"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <div className="flex items-center gap-3">
          <button className="text-muted-foreground hover:text-foreground transition-colors">
            {isExpanded ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
          </button>
          <FileCode2 className="h-4 w-4 text-muted-foreground" />
          <span className="text-sm font-medium text-foreground font-mono">{file}</span>
        </div>
        <div className="flex items-center gap-4 text-xs font-medium">
          <span className="text-success">+{additions}</span>
          <span className="text-critical">-{deletions}</span>
        </div>
      </div>

      {/* Diff Content */}
      {isExpanded && (
        <div className="overflow-x-auto">
          <table className="w-full text-sm font-mono border-collapse">
            <tbody className="divide-y divide-transparent">
              {lines.map((line, idx) => {
                const isAdded = line.startsWith("+")
                const isRemoved = line.startsWith("-")
                const isContext = !isAdded && !isRemoved

                // Basic highlighting logic
                const bgColor = isAdded ? "bg-success/10" : isRemoved ? "bg-critical/10" : "bg-transparent"
                const textColor = isAdded ? "text-success-foreground" : isRemoved ? "text-critical-foreground" : "text-muted-foreground"
                const symbol = isAdded ? "+" : isRemoved ? "-" : " "

                // Remove the first char for display if it's diff syntax
                const displayLine = line.length > 0 && (isAdded || isRemoved || line.startsWith(" ")) ? line.substring(1) : line

                return (
                  <tr key={idx} className={cn("group hover:bg-secondary/20", bgColor)}>
                    <td className="w-12 px-2 py-0.5 text-right text-xs text-muted-foreground/50 select-none border-r border-border bg-card">
                      {isContext || isRemoved ? idx + 1 : ""}
                    </td>
                    <td className="w-12 px-2 py-0.5 text-right text-xs text-muted-foreground/50 select-none border-r border-border bg-card">
                      {isContext || isAdded ? idx + 1 : ""}
                    </td>
                    <td className={cn("px-4 py-0.5 whitespace-pre select-text", textColor)}>
                      <span className="inline-block w-4 opacity-50 select-none">{symbol}</span>
                      <span className="text-foreground">{displayLine}</span>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
