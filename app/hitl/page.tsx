"use client"

import { useEffect, useState } from "react"
import { AppShell } from "@/components/app-shell"
import { PageHeader } from "@/components/page-header"
import { apiClient } from "@/lib/api-client"
import { HitlItem } from "@/lib/types"
import { useToast } from "@/hooks/use-toast"
import { SeverityBadge } from "@/components/severity-badge"
import { TableSkeleton } from "@/components/loading-skeleton"
import { Clock, Check, X, ShieldAlert, ArrowRight } from "lucide-react"
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
        <div className="bg-card border border-border rounded-xl shadow-sm p-6 mt-6">
          <TableSkeleton rows={4} />
        </div>
      ) : items.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-24 text-center bg-card border border-border rounded-xl mt-6 shadow-sm">
          <div className="bg-secondary/50 p-4 rounded-full mb-4">
            <Check className="h-8 w-8 text-success" />
          </div>
          <h2 className="text-xl font-semibold text-foreground">All Caught Up!</h2>
          <p className="text-muted-foreground mt-2 max-w-sm">
            There are no pending code reviews requiring manual approval in the HITL queue.
          </p>
        </div>
      ) : (
        <div className="grid gap-6 mt-6">
          {items.map((item) => (
            <div key={item.id} className="flex flex-col lg:flex-row gap-6 p-6 bg-card border border-border rounded-xl shadow-sm transition-all hover:border-border/80 relative overflow-hidden">
              {/* Highlight bar on left */}
              <div className="absolute left-0 top-0 bottom-0 w-1 bg-warning/80" />
              
              <div className="flex-1 space-y-4">
                <div className="flex items-start justify-between">
                  <div>
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-sm font-medium text-muted-foreground">{item.repoName}</span>
                      <span className="text-sm text-muted-foreground">#{item.pullRequestNumber}</span>
                    </div>
                    <h3 className="text-lg font-semibold text-foreground">{item.title}</h3>
                  </div>
                  <SeverityBadge level={item.severity} />
                </div>

                <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 bg-secondary/20 p-4 rounded-lg border border-border/50">
                  <div>
                    <p className="text-xs text-muted-foreground uppercase tracking-wider mb-1">Critical Issues</p>
                    <p className="text-lg font-bold text-critical flex items-center gap-2">
                      <ShieldAlert className="h-4 w-4" />
                      {item.findingsCount}
                    </p>
                  </div>
                  <div>
                    <p className="text-xs text-muted-foreground uppercase tracking-wider mb-1">ACS Score</p>
                    <p className="text-lg font-bold text-foreground">{item.acsScore}</p>
                  </div>
                  <div>
                    <p className="text-xs text-muted-foreground uppercase tracking-wider mb-1">Changes</p>
                    <p className="text-sm font-medium text-foreground mt-1">
                      <span className="text-success">+{item.linesAdded}</span> / <span className="text-critical">-{item.linesDeleted}</span>
                    </p>
                  </div>
                  <div>
                    <p className="text-xs text-muted-foreground uppercase tracking-wider mb-1">Waiting Since</p>
                    <p className="text-sm font-medium text-foreground flex items-center gap-1.5 mt-1">
                      <Clock className="h-3.5 w-3.5 text-muted-foreground" />
                      {new Date(item.waitingSince).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    </p>
                  </div>
                </div>
              </div>

              <div className="flex lg:flex-col justify-end gap-3 lg:w-48 shrink-0 border-t lg:border-t-0 lg:border-l border-border pt-4 lg:pt-0 lg:pl-6">
                <button
                  onClick={() => handleAction(item.id, "approve")}
                  disabled={actionLoading !== null}
                  className="flex-1 lg:flex-none flex items-center justify-center gap-2 px-4 py-2 bg-success text-success-foreground hover:bg-success/90 rounded-md font-medium text-sm transition-colors disabled:opacity-50"
                >
                  {actionLoading === item.id ? <span className="h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent" /> : <Check className="h-4 w-4" />}
                  Approve
                </button>
                <button
                  onClick={() => handleAction(item.id, "reject")}
                  disabled={actionLoading !== null}
                  className="flex-1 lg:flex-none flex items-center justify-center gap-2 px-4 py-2 bg-critical text-critical-foreground hover:bg-critical/90 rounded-md font-medium text-sm transition-colors disabled:opacity-50"
                >
                  {actionLoading === item.id ? <span className="h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent" /> : <X className="h-4 w-4" />}
                  Reject
                </button>
                <button
                  onClick={() => router.push(`/reviews/${item.id}`)}
                  disabled={actionLoading !== null}
                  className="flex-1 lg:flex-none flex items-center justify-center gap-2 px-4 py-2 bg-secondary text-secondary-foreground hover:bg-secondary/80 rounded-md font-medium text-sm transition-colors disabled:opacity-50"
                >
                  View Details
                  <ArrowRight className="h-4 w-4" />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </AppShell>
  )
}
