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

export function DiffViewer({
  file,
  content,
  additions,
  deletions,
  defaultExpanded = true,
}: DiffViewerProps) {
  const [isExpanded, setIsExpanded] = useState(defaultExpanded)
  const lines = content ? content.split("\n") : []

  return (
    <div className="rounded-xl border border-border bg-card overflow-hidden w-full max-w-full min-w-0 shadow-xs">
      {/* Interactive Header */}
      <button
        type="button"
        onClick={() => setIsExpanded(!isExpanded)}
        aria-expanded={isExpanded}
        className="w-full flex items-center justify-between px-4 py-3 min-h-[44px] bg-secondary/30 border-b border-border text-left hover:bg-secondary/50 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-inset"
      >
        <div className="flex items-center gap-3 min-w-0 pr-4">
          <span className="text-muted-foreground shrink-0">
            {isExpanded ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
          </span>
          <FileCode2 className="h-4 w-4 text-muted-foreground shrink-0" />
          <span className="text-sm font-medium text-foreground font-mono truncate">{file}</span>
        </div>
        <div className="flex items-center gap-3 text-xs font-semibold shrink-0 font-mono">
          <span className="text-success">+{additions}</span>
          <span className="text-critical">-{deletions}</span>
        </div>
      </button>

      {/* Internal Scrollable Diff Table */}
      {isExpanded && (
        <div className="overflow-x-auto max-w-full min-w-0">
          <table className="w-full text-xs font-mono border-collapse min-w-[500px]">
            <tbody className="divide-y divide-transparent">
              {lines.map((line, idx) => {
                const isAdded = line.startsWith("+")
                const isRemoved = line.startsWith("-")
                const isContext = !isAdded && !isRemoved

                const bgColor = isAdded
                  ? "bg-success/10"
                  : isRemoved
                  ? "bg-critical/10"
                  : "bg-transparent"
                const textColor = isAdded
                  ? "text-success-foreground"
                  : isRemoved
                  ? "text-critical-foreground"
                  : "text-muted-foreground"
                const symbol = isAdded ? "+" : isRemoved ? "-" : " "

                const displayLine =
                  line.length > 0 && (isAdded || isRemoved || line.startsWith(" "))
                    ? line.substring(1)
                    : line

                return (
                  <tr key={idx} className={cn("group hover:bg-secondary/20", bgColor)}>
                    <td className="w-10 px-2 py-0.5 text-right text-caption text-muted-foreground/50 select-none border-r border-border bg-card shrink-0">
                      {isContext || isRemoved ? idx + 1 : ""}
                    </td>
                    <td className="w-10 px-2 py-0.5 text-right text-caption text-muted-foreground/50 select-none border-r border-border bg-card shrink-0">
                      {isContext || isAdded ? idx + 1 : ""}
                    </td>
                    <td className={cn("px-4 py-0.5 whitespace-pre select-text min-w-0", textColor)}>
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
