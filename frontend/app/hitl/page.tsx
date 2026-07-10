"use client"

import { useEffect, useState } from "react"
import { AppShell } from "@/components/app-shell"
import { PageHeader } from "@/components/page-header"
import { apiClient } from "@/lib/api-client"
import { HitlItem } from "@/lib/types"
import { useToast } from "@/hooks/use-toast"
import { SeverityBadge } from "@/components/severity-badge"
import { TableSkeleton } from "@/components/loading-skeleton"
import { Clock, Check, X, ShieldAlert, ArrowRight, Sparkles } from "lucide-react"
import { useRouter } from "next/navigation"

export default function HitlPage() {
  const router = useRouter()
  const { toast } = useToast()
  const [loading, setLoading] = useState(true)
  const [items, setItems] = useState<HitlItem[]>([])
  const [actionLoading, setActionLoading] = useState<string | null>(null)

  useEffect(() => {
    async function load() {
      try {
        const data = await apiClient.getHitlPending()
        setItems(data)
      } catch {
        toast({ title: "Error", description: "Failed to load HITL queue", type: "error" })
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [toast])

  const handleAction = async (id: string, action: "approve" | "reject") => {
    if (!confirm(`Are you sure you want to ${action} this code review?`)) return

    setActionLoading(id)
    try {
      if (action === "approve") {
        await apiClient.approveHitl(id)
        toast({ title: "Approved", description: "Review has been approved successfully.", type: "success" })
      } else {
        await apiClient.rejectHitl(id)
        toast({ title: "Rejected", description: "Review has been rejected.", type: "warning" })
      }
      // Optimistic UI update
      setItems(items.filter(item => item.id !== id))
    } catch {
      toast({ title: "Error", description: `Failed to ${action} review.`, type: "error" })
    } finally {
      setActionLoading(null)
    }
  }

  return (
    <AppShell>
      <PageHeader 
        title="Human-in-the-Loop (HITL)" 
        description="Manual approval queue for reviews flagged with critical security or architectural regressions."
      />

      {loading ? (
        <div className="bg-[#14171A] border border-[#22262B] rounded-xl shadow-lg p-6 mt-6">
          <TableSkeleton rows={4} />
        </div>
      ) : items.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-20 text-center bg-[#14171A] border border-[#22262B] rounded-xl mt-6 shadow-lg shadow-black/30">
          <div className="bg-success/10 border border-success/30 p-4 rounded-full mb-4">
            <Check className="h-8 w-8 text-success" />
          </div>
          <h2 className="text-xl font-bold text-foreground">All Caught Up!</h2>
          <p className="text-muted-foreground mt-2 max-w-sm text-sm">
            There are no pending code reviews requiring manual approval in the HITL queue.
          </p>
        </div>
      ) : (
        <div className="grid gap-6 mt-6">
          {items.map((item) => (
            <div key={item.id} className="flex flex-col lg:flex-row gap-6 p-6 bg-[#14171A] border border-[#22262B] rounded-xl shadow-lg shadow-black/20 transition-all duration-300 hover:border-[#22262B]/80 relative overflow-hidden group">
              {/* Highlight bar on left based on severity */}
              <div className="absolute left-0 top-0 bottom-0 w-1.5 bg-warning/80 shadow-[0_0_8px_rgba(201,162,39,0.3)]" />
              
              <div className="flex-1 space-y-4">
                <div className="flex items-start justify-between gap-4">
                  <div className="space-y-1">
                    <div className="flex items-center gap-2 text-xs font-mono text-muted-foreground">
                      <span className="font-semibold text-foreground/80 hover:text-primary transition-colors">{item.repoName}</span>
                      <span className="text-muted-foreground/50">#{item.pullRequestNumber}</span>
                    </div>
                    <h3 className="text-base font-bold text-foreground group-hover:text-primary transition-colors line-clamp-1">{item.title}</h3>
                  </div>
                  <SeverityBadge level={item.severity} className="shrink-0" />
                </div>

                <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 bg-[#0B0D0F]/40 p-4 rounded-lg border border-[#22262B]/50 font-mono">
                  <div className="space-y-1">
                    <p className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider">Critical Issues</p>
                    <p className="text-base font-extrabold text-critical flex items-center gap-1.5">
                      <ShieldAlert className="h-4 w-4 shrink-0" />
                      {item.findingsCount}
                    </p>
                  </div>
                  <div className="space-y-1">
                    <p className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider">ACS Score</p>
                    <p className="text-base font-extrabold text-foreground">{item.acsScore}</p>
                  </div>
                  <div className="space-y-1">
                    <p className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider">Changes</p>
                    <p className="text-xs font-bold text-foreground mt-0.5">
                      <span className="text-success">+{item.linesAdded}</span>
                      <span className="text-muted-foreground/30 px-1">/</span>
                      <span className="text-critical">-{item.linesDeleted}</span>
                    </p>
                  </div>
                  <div className="space-y-1">
                    <p className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider">Waiting Since</p>
                    <p className="text-xs font-semibold text-foreground flex items-center gap-1.5 mt-0.5">
                      <Clock className="h-3.5 w-3.5 text-muted-foreground shrink-0" />
                      {new Date(item.waitingSince).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    </p>
                  </div>
                </div>
              </div>

              <div className="flex lg:flex-col justify-end gap-3 lg:w-48 shrink-0 border-t lg:border-t-0 lg:border-l border-[#22262B] pt-4 lg:pt-0 lg:pl-6">
                <button
                  onClick={() => handleAction(item.id, "approve")}
                  disabled={actionLoading !== null}
                  className="flex-1 lg:flex-none flex items-center justify-center gap-2 px-4 py-2 bg-success text-success-foreground hover:bg-success/90 rounded-lg font-semibold text-xs transition-all disabled:opacity-50 shadow-md shadow-success/10 font-mono uppercase tracking-wider"
                >
                  {actionLoading === item.id ? <span className="h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent" /> : <Check className="h-3.5 w-3.5" />}
                  Approve
                </button>
                <button
                  onClick={() => handleAction(item.id, "reject")}
                  disabled={actionLoading !== null}
                  className="flex-1 lg:flex-none flex items-center justify-center gap-2 px-4 py-2 bg-critical text-critical-foreground hover:bg-critical/90 rounded-lg font-semibold text-xs transition-all disabled:opacity-50 shadow-md shadow-critical/10 font-mono uppercase tracking-wider"
                >
                  {actionLoading === item.id ? <span className="h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent" /> : <X className="h-3.5 w-3.5" />}
                  Reject
                </button>
                <button
                  onClick={() => router.push(`/reviews/${item.id}`)}
                  disabled={actionLoading !== null}
                  className="flex-1 lg:flex-none flex items-center justify-center gap-2 px-4 py-2 bg-[#14171A] border border-[#22262B] text-foreground hover:bg-[#1C1F22] rounded-lg font-semibold text-xs transition-all disabled:opacity-50 font-mono uppercase tracking-wider"
                >
                  View Details
                  <ArrowRight className="h-3.5 w-3.5" />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </AppShell>
  )
}
