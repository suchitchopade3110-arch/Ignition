"use client"

import { useState, useEffect } from "react"
import { AppShell } from "@/components/layout/app-shell"
import { PageHeader } from "@/components/layout/page-header"
import { StatusBadge } from "@/components/ui/status-badge"
import { AcsScoreRing } from "@/components/ui/acs-score-ring"
import { useRouter } from "next/navigation"
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Area, AreaChart } from "recharts"
import { GitCommit, Activity, ShieldAlert, TrendingDown, ChevronDown, Calendar, ChevronRight } from "lucide-react"
import { ErrorState } from "@/components/ui/error-state"
import { ApiError } from "@/lib/errors"
import { useRepositories } from "@/hooks/queries/use-repositories"
import { useLedgerStats, useLedgerTrend } from "@/hooks/queries/use-ledger"
import { useRepoReviews } from "@/hooks/queries/use-repo-reviews"

export default function LedgerPage() {
  const router = useRouter()
  const {
    data: repos = [],
    isLoading: isReposLoading,
    isError: isReposError,
    error: reposError,
    refetch: refetchRepos,
  } = useRepositories()
  const [selectedRepo, setSelectedRepo] = useState<string>("")

  // Initialize selected repo when repositories load
  useEffect(() => {
    if (repos.length > 0 && !selectedRepo) {
      setSelectedRepo(`${repos[0].owner}/${repos[0].name}`)
    }
  }, [repos, selectedRepo])

  const {
    data: stats,
    isLoading: isStatsLoading,
    isError: isStatsError,
    error: statsError,
    refetch: refetchStats,
  } = useLedgerStats(selectedRepo)

  const {
    data: trend = [],
    isLoading: isTrendLoading,
    isError: isTrendError,
    error: trendError,
    refetch: refetchTrend,
  } = useLedgerTrend(selectedRepo)

  const {
    data: reviewsData,
    isLoading: isReviewsLoading,
    isError: isReviewsError,
    error: reviewsError,
    refetch: refetchReviews,
  } = useRepoReviews(selectedRepo)
  const reviews = reviewsData?.items ?? []

  const isLoading = isReposLoading || isStatsLoading || isTrendLoading || isReviewsLoading
  const isError = isReposError || isStatsError || isTrendError || isReviewsError

  const getErrorMessage = () => {
    const err = reposError || statsError || trendError || reviewsError
    if (err instanceof ApiError) return err.getUserMessage()
    if (err instanceof Error) return err.message
    return "Failed to load security ledger data. Please try again."
  }

  const handleRetry = () => {
    refetchRepos()
    refetchStats()
    refetchTrend()
    refetchReviews()
  }

  interface TooltipProps {
    active?: boolean
    payload?: Array<{ color: string; name: string; value: number | string }>
    label?: string
  }

  const CustomTooltip = ({ active, payload, label }: TooltipProps) => {
    if (active && payload && payload.length) {
      return (
        <div className="bg-elevated border border-border p-3 rounded-lg font-mono tabular-nums text-xs">
          <p className="text-sm font-bold text-foreground mb-2">{label}</p>
          {payload.map((entry, index: number) => (
            <p key={index} className="text-xs py-0.5" style={{ color: entry.color }}>
              {entry.name}: <span className="font-bold text-foreground">{entry.value}</span>
            </p>
          ))}
        </div>
      )
    }
    return null
  }

  return (
    <AppShell>
      <div className="flex flex-col sm:flex-row sm:items-center justify-between mb-8 gap-4 border-b border-border pb-6">
        <PageHeader
          title="Security Ledger"
          description="Historical AI review metrics and Architecture Compliance Score (ACS) trends."
        />
        {repos.length > 0 && (
          <div className="relative shrink-0 self-start sm:self-center w-full sm:w-auto">
            <select
              value={selectedRepo}
              onChange={(e) => setSelectedRepo(e.target.value)}
              aria-label="Select repository for ledger analysis"
              className="appearance-none w-full sm:w-64 min-h-[44px] bg-card border border-white/[0.08] text-foreground text-xs font-semibold rounded-lg focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary block p-2.5 pr-10 transition-colors hover:border-white/[0.12] cursor-pointer shadow-[inset_0_1px_0_0_rgba(255,255,255,0.03)]"
            >
              {repos.map((r) => (
                <option key={r.id} value={`${r.owner}/${r.name}`} className="bg-card text-foreground">
                  {r.name}
                </option>
              ))}
            </select>
            <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground pointer-events-none" />
          </div>
        )}
      </div>

      {isLoading ? (
        <div className="space-y-8">
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4">
            {[1, 2, 3, 4].map((i) => (
              <div key={i} className="bg-card border border-white/[0.08] rounded-xl p-6 h-24 animate-pulse" />
            ))}
          </div>
          <div className="bg-card border border-white/[0.08] rounded-xl p-6 h-[380px] animate-pulse" />
        </div>
      ) : isError ? (
        <div className="py-6">
          <ErrorState
            title="Unable to load ledger metrics"
            message={getErrorMessage()}
            onRetry={handleRetry}
          />
        </div>
      ) : (
        <>
          {stats && (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
              <div className="bg-card border border-white/[0.08] rounded-xl p-5 shadow-[inset_0_1px_0_0_rgba(255,255,255,0.03)] hover:border-white/[0.12] transition-colors">
                <div className="flex items-center gap-2 mb-2">
                  <Activity className="h-4 w-4 text-primary" />
                  <p className="text-xs font-bold uppercase tracking-wider text-muted-foreground">Average ACS</p>
                </div>
                <p className="text-2xl font-extrabold text-foreground font-mono tabular-nums">{stats.averageAcs}</p>
              </div>
              <div className="bg-card border border-white/[0.08] rounded-xl p-5 shadow-[inset_0_1px_0_0_rgba(255,255,255,0.03)] hover:border-white/[0.12] transition-colors">
                <div className="flex items-center gap-2 mb-2">
                  <GitCommit className="h-4 w-4 text-success" />
                  <p className="text-xs font-bold uppercase tracking-wider text-muted-foreground">Total Reviews</p>
                </div>
                <p className="text-2xl font-extrabold text-foreground font-mono tabular-nums">{stats.totalReviews}</p>
              </div>
              <div className="bg-card border border-white/[0.08] rounded-xl p-5 shadow-[inset_0_1px_0_0_rgba(255,255,255,0.03)] hover:border-white/[0.12] transition-colors">
                <div className="flex items-center gap-2 mb-2">
                  <ShieldAlert className="h-4 w-4 text-critical" />
                  <p className="text-xs font-bold uppercase tracking-wider text-muted-foreground">Critical Findings</p>
                </div>
                <p className="text-2xl font-extrabold text-foreground font-mono tabular-nums">{stats.criticalFindings}</p>
              </div>
              <div className="bg-card border border-white/[0.08] rounded-xl p-5 shadow-[inset_0_1px_0_0_rgba(255,255,255,0.03)] hover:border-white/[0.12] transition-colors">
                <div className="flex items-center gap-2 mb-2">
                  <TrendingDown className="h-4 w-4 text-warning" />
                  <p className="text-xs font-bold uppercase tracking-wider text-muted-foreground">Active Regressions</p>
                </div>
                <p className="text-2xl font-extrabold text-foreground font-mono tabular-nums">{stats.activeRegressions}</p>
              </div>
            </div>
          )}

          {trend.length > 0 && (
            <div className="bg-card border border-white/[0.08] rounded-xl p-4 sm:p-6 mb-8 overflow-hidden shadow-[inset_0_1px_0_0_rgba(255,255,255,0.03)]">
              <h3 className="text-xs font-bold uppercase tracking-wider text-foreground mb-6 border-b border-white/[0.06] pb-3">
                ACS Trend Line
              </h3>
              <div className="h-[260px] sm:h-[300px] w-full min-w-0">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={trend} margin={{ top: 10, right: 10, left: -25, bottom: 0 }}>
                    <defs>
                      <linearGradient id="colorAcs" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#FF4500" stopOpacity={0.25} />
                        <stop offset="95%" stopColor="#FF4500" stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" vertical={false} />
                    <XAxis dataKey="date" stroke="#71717A" fontSize={10} tickLine={false} axisLine={false} dy={10} className="font-mono tabular-nums" />
                    <YAxis stroke="#71717A" fontSize={10} tickLine={false} axisLine={false} domain={["auto", 100]} className="font-mono tabular-nums" />
                    <Tooltip content={<CustomTooltip />} cursor={{ stroke: "rgba(255,255,255,0.1)", strokeWidth: 1 }} />
                    <Area
                      type="monotone"
                      dataKey="acsScore"
                      name="ACS Score"
                      stroke="#FF4500"
                      strokeWidth={2}
                      fillOpacity={1}
                      fill="url(#colorAcs)"
                      animationDuration={800}
                    />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </div>
          )}

          {trend.length > 0 && (
            <div className="bg-card border border-white/[0.08] rounded-xl p-4 sm:p-6 mb-8 overflow-hidden shadow-[inset_0_1px_0_0_rgba(255,255,255,0.03)]">
              <h3 className="text-xs font-bold uppercase tracking-wider text-foreground mb-6 border-b border-white/[0.06] pb-3">
                Critical Findings vs Total Reviews
              </h3>
              <div className="h-[260px] sm:h-[300px] w-full min-w-0">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={trend} margin={{ top: 10, right: 10, left: -25, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" vertical={false} />
                    <XAxis dataKey="date" stroke="#71717A" fontSize={10} tickLine={false} axisLine={false} dy={10} className="font-mono tabular-nums" />
                    <YAxis yAxisId="left" stroke="#71717A" fontSize={10} tickLine={false} axisLine={false} className="font-mono tabular-nums" />
                    <YAxis yAxisId="right" orientation="right" stroke="#71717A" fontSize={10} tickLine={false} axisLine={false} className="font-mono tabular-nums" />
                    <Tooltip content={<CustomTooltip />} cursor={{ stroke: "rgba(255,255,255,0.1)", strokeWidth: 1 }} />
                    <Line
                      yAxisId="left"
                      type="monotone"
                      dataKey="reviewsCount"
                      name="Total Reviews"
                      stroke="#10B981"
                      strokeWidth={2}
                      dot={{ r: 3, strokeWidth: 2, fill: "#18181B" }}
                      activeDot={{ r: 5 }}
                      animationDuration={800}
                    />
                    <Line
                      yAxisId="right"
                      type="monotone"
                      dataKey="criticalCount"
                      name="Critical Findings"
                      stroke="#DC2626"
                      strokeWidth={2}
                      dot={{ r: 3, strokeWidth: 2, fill: "#18181B" }}
                      activeDot={{ r: 5 }}
                      animationDuration={800}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </div>
          )}

          {/* Historical Review List */}
          {reviews.length > 0 && (
            <div className="bg-card border border-white/[0.08] rounded-xl overflow-hidden shadow-[inset_0_1px_0_0_rgba(255,255,255,0.03)]">
              <h3 className="text-xs font-bold uppercase tracking-wider text-foreground p-6 border-b border-white/[0.06] pb-3 bg-white/[0.02]">
                Historical Reviews
              </h3>

              {/* Desktop View: Semantic Table */}
              <div className="hidden sm:block overflow-x-auto min-w-0 p-6 pt-0">
                <table className="w-full text-left text-xs border-collapse">
                  <thead>
                    <tr className="border-b border-white/[0.06] text-muted-foreground">
                      <th className="pb-3 pt-4 font-semibold uppercase tracking-wider">Pull Request</th>
                      <th className="pb-3 pt-4 font-semibold uppercase tracking-wider">Status</th>
                      <th className="pb-3 pt-4 font-semibold uppercase tracking-wider">Duration</th>
                      <th className="pb-3 pt-4 font-semibold uppercase tracking-wider text-right">ACS</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-white/[0.04]">
                    {reviews.map((rev) => (
                      <tr
                        key={rev.id}
                        tabIndex={0}
                        role="link"
                        aria-label={`View review for ${rev.title}`}
                        className="hover:bg-white/[0.02] transition-colors cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-inset"
                        onClick={() => router.push(`/reviews/${rev.id}`)}
                        onKeyDown={(e) => {
                          if (e.key === "Enter" || e.key === " ") {
                            e.preventDefault()
                            router.push(`/reviews/${rev.id}`)
                          }
                        }}
                      >
                        <td className="py-3.5 pr-4">
                          <div className="flex flex-col gap-1">
                            <span className="font-semibold text-foreground hover:text-primary transition-colors text-sm">{rev.title}</span>
                            <div className="flex items-center gap-2 text-muted-foreground font-mono tabular-nums text-[10px]">
                              <span>#{rev.pullRequestNumber}</span>
                              <span>•</span>
                              <span className="flex items-center gap-1">
                                <Calendar className="h-3 w-3" />
                                {new Date(rev.createdAt).toLocaleDateString()}
                              </span>
                            </div>
                          </div>
                        </td>
                        <td className="py-3.5">
                          <StatusBadge status={rev.status} />
                        </td>
                        <td className="py-3.5 text-muted-foreground font-mono tabular-nums">
                          {rev.duration || "N/A"}
                        </td>
                        <td className="py-3.5 text-right font-mono tabular-nums">
                          <div className="flex justify-end">
                            {rev.acsScore !== undefined ? (
                              <AcsScoreRing score={rev.acsScore} size={28} strokeWidth={2.5} />
                            ) : (
                              <span className="text-muted-foreground/40">N/A</span>
                            )}
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* Mobile View: Stacked Cards (< sm) */}
              <div className="sm:hidden divide-y divide-white/[0.04]">
                {reviews.map((rev) => (
                  <div
                    key={rev.id}
                    tabIndex={0}
                    role="link"
                    aria-label={`View review for ${rev.title}`}
                    onClick={() => router.push(`/reviews/${rev.id}`)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter" || e.key === " ") {
                        e.preventDefault()
                        router.push(`/reviews/${rev.id}`)
                      }
                    }}
                    className="p-4 space-y-3 hover:bg-white/[0.03] active:bg-white/[0.05] transition-colors cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-inset"
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div className="space-y-1 min-w-0 flex-1">
                        <span className="text-[10px] font-mono tabular-nums text-muted-foreground block">
                          #{rev.pullRequestNumber}
                        </span>
                        <h4 className="font-semibold text-foreground text-sm line-clamp-2">
                          {rev.title}
                        </h4>
                      </div>
                      <div className="shrink-0 flex items-center gap-1.5 pt-0.5">
                        {rev.acsScore !== undefined ? (
                          <AcsScoreRing score={rev.acsScore} size={30} strokeWidth={2.5} />
                        ) : (
                          <span className="text-muted-foreground/40 text-xs font-mono">N/A</span>
                        )}
                        <ChevronRight className="h-4 w-4 text-muted-foreground/60" />
                      </div>
                    </div>

                    <div className="flex items-center justify-between gap-2 pt-1 border-t border-white/[0.04] text-xs">
                      <StatusBadge status={rev.status} />
                      <div className="flex items-center gap-3 text-muted-foreground font-mono tabular-nums text-[11px]">
                        <span>{rev.duration || "N/A"}</span>
                        <span className="flex items-center gap-1">
                          <Calendar className="h-3 w-3" />
                          {new Date(rev.createdAt).toLocaleDateString()}
                        </span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </>
      )}
    </AppShell>
  )
}
