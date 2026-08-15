"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import { AppShell } from "@/components/layout/app-shell"
import { PageHeader } from "@/components/layout/page-header"
import { useToast } from "@/hooks/use-toast"
import { SeverityBadge } from "@/components/ui/severity-badge"
import { TableSkeleton } from "@/components/ui/loading-skeleton"
import { Clock, Check, X, ShieldAlert, ArrowRight } from "lucide-react"
import { ErrorState } from "@/components/ui/error-state"
import { ApiError } from "@/lib/errors"
import { useHitlPending } from "@/hooks/queries/use-hitl-pending"
import { useApproveHitlMutation, useRejectHitlMutation } from "@/hooks/mutations/use-hitl-mutation"

export default function HitlPage() {
  const router = useRouter()
  const { toast } = useToast()
  const { data: items = [], isLoading, isError, error, refetch } = useHitlPending()
  const approveMutation = useApproveHitlMutation()
  const rejectMutation = useRejectHitlMutation()

  const [activeItemId, setActiveItemId] = useState<string | null>(null)

  const isMutating = approveMutation.isPending || rejectMutation.isPending

  const getErrorMessage = () => {
    if (error instanceof ApiError) return error.getUserMessage()
    if (error instanceof Error) return error.message
    return "Failed to load approval queue. Please try again."
  }

  const handleAction = async (id: string, action: "approve" | "reject") => {
    if (isMutating) return
    if (!confirm(`Are you sure you want to ${action} this code review?`)) return

    setActiveItemId(id)
    try {
      if (action === "approve") {
        await approveMutation.mutateAsync(id)
        toast({ title: "Approved", description: "Review has been approved successfully.", type: "success" })
      } else {
        await rejectMutation.mutateAsync(id)
        toast({ title: "Rejected", description: "Review has been rejected.", type: "warning" })
      }
    } catch (err: unknown) {
      const msg = err instanceof ApiError ? err.getUserMessage() : `Failed to ${action} review.`
      toast({ title: "Error", description: msg, type: "error" })
    } finally {
      setActiveItemId(null)
    }
  }

  return (
    <AppShell>
      <PageHeader
        title="Human-in-the-Loop (HITL)"
        description="Manual approval queue for reviews flagged with critical security or architectural regressions."
      />

      {isLoading ? (
        <div className="bg-card/60 backdrop-blur-md border border-white/[0.08] rounded-xl p-6 mt-6 shadow-[inset_0_1px_0_0_rgba(255,255,255,0.03)]">
          <TableSkeleton rows={4} />
        </div>
      ) : isError ? (
        <div className="mt-6">
          <ErrorState
            title="Unable to load approval queue"
            message={getErrorMessage()}
            onRetry={() => refetch()}
          />
        </div>
      ) : items.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-20 text-center bg-card/60 backdrop-blur-md border border-white/[0.08] rounded-xl mt-6 px-6 shadow-[inset_0_1px_0_0_rgba(255,255,255,0.03)]">
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
          {items.map((item) => {
            const isCurrentItemLoading = isMutating && activeItemId === item.id

            return (
              <div
                key={item.id}
                className="flex flex-col lg:flex-row gap-6 p-4 sm:p-6 bg-card/60 backdrop-blur-md border border-white/[0.08] shadow-[inset_0_1px_0_0_rgba(255,255,255,0.03)] rounded-xl transition-colors hover:border-white/[0.12] relative overflow-hidden group"
              >
                {/* Highlight bar on left based on severity */}
                <div className="absolute left-0 top-0 bottom-0 w-1.5 bg-warning/80" />

                <div className="flex-1 space-y-4 min-w-0">
                  <div className="flex items-start justify-between gap-4">
                    <div className="space-y-1 min-w-0 flex-1">
                      <div className="flex items-center gap-2 text-xs font-mono tabular-nums text-muted-foreground">
                        <span className="font-semibold text-foreground/80 hover:text-primary transition-colors truncate">
                          {item.repoName}
                        </span>
                        <span className="text-muted-foreground/50">#{item.pullRequestNumber}</span>
                      </div>
                      <h3 className="text-base font-bold text-foreground group-hover:text-primary transition-colors line-clamp-2">
                        {item.title}
                      </h3>
                    </div>
                    <SeverityBadge level={item.severity} className="shrink-0" />
                  </div>

                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 bg-black/30 p-3 sm:p-4 rounded-lg border border-white/[0.04] font-mono tabular-nums">
                    <div className="space-y-1">
                      <p className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider">Critical Issues</p>
                      <p className="text-sm sm:text-base font-extrabold text-critical flex items-center gap-1.5">
                        <ShieldAlert className="h-4 w-4 shrink-0" />
                        {item.findingsCount}
                      </p>
                    </div>
                    <div className="space-y-1">
                      <p className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider">ACS Score</p>
                      <p className="text-sm sm:text-base font-extrabold text-foreground">{item.acsScore}</p>
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
                        {new Date(item.waitingSince).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                      </p>
                    </div>
                  </div>
                </div>

                <div className="flex flex-col sm:flex-row lg:flex-col justify-end gap-3 lg:w-48 shrink-0 border-t lg:border-t-0 lg:border-l border-white/[0.06] pt-4 lg:pt-0 lg:pl-6">
                  <button
                    type="button"
                    onClick={() => handleAction(item.id, "approve")}
                    disabled={isMutating}
                    className="w-full flex items-center justify-center gap-2 min-h-[44px] px-4 py-2.5 bg-success text-success-foreground hover:bg-success/90 rounded-lg font-semibold text-xs transition-colors disabled:opacity-50 font-mono uppercase tracking-wider focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 focus-visible:ring-offset-card"
                  >
                    {isCurrentItemLoading && approveMutation.isPending ? (
                      <span className="h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent" />
                    ) : (
                      <Check className="h-4 w-4" />
                    )}
                    Approve
                  </button>
                  <button
                    type="button"
                    onClick={() => handleAction(item.id, "reject")}
                    disabled={isMutating}
                    className="w-full flex items-center justify-center gap-2 min-h-[44px] px-4 py-2.5 bg-critical text-critical-foreground hover:bg-critical/90 rounded-lg font-semibold text-xs transition-colors disabled:opacity-50 font-mono uppercase tracking-wider focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 focus-visible:ring-offset-card"
                  >
                    {isCurrentItemLoading && rejectMutation.isPending ? (
                      <span className="h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent" />
                    ) : (
                      <X className="h-4 w-4" />
                    )}
                    Reject
                  </button>
                  <button
                    type="button"
                    onClick={() => router.push(`/reviews/${item.id}`)}
                    disabled={isMutating}
                    className="w-full flex items-center justify-center gap-2 min-h-[44px] px-4 py-2.5 bg-white/[0.04] border border-white/[0.08] text-foreground hover:bg-white/[0.08] rounded-lg font-semibold text-xs transition-colors disabled:opacity-50 font-mono uppercase tracking-wider focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 focus-visible:ring-offset-card"
                  >
                    View Details
                    <ArrowRight className="h-4 w-4" />
                  </button>
                </div>
              </div>
            )
          })}
        </div>
      )}
    </AppShell>
  )
}
