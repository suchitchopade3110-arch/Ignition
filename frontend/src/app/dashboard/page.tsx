"use client"

import Link from "next/link"
import { AppShell } from "@/components/layout/app-shell"
import { PageHeader } from "@/components/layout/page-header"
import { StatsCard } from "@/components/dashboard/stats-card"
import { Activity, ShieldAlert, GitPullRequest, Code2, ArrowRight } from "lucide-react"
import { AcsScoreRing } from "@/components/ui/acs-score-ring"
import { SeverityBadge } from "@/components/ui/severity-badge"
import { AnimatedAcsScore } from "@/components/ui/animated-acs-score"
import { useDashboardStats } from "@/hooks/queries/use-dashboard-stats"
import { useReviews } from "@/hooks/queries/use-reviews"
import { useRepositories } from "@/hooks/queries/use-repositories"
import { CardSkeleton } from "@/components/ui/loading-skeleton"
import { ErrorState } from "@/components/ui/error-state"
import { ApiError } from "@/lib/errors"

export default function DashboardPage() {
  const {
    data: stats,
    isLoading: isStatsLoading,
    isError: isStatsError,
    error: statsError,
    refetch: refetchStats,
  } = useDashboardStats()

  const {
    data: reviews = [],
    isLoading: isReviewsLoading,
    isError: isReviewsError,
    error: reviewsError,
    refetch: refetchReviews,
  } = useReviews()

  const {
    data: repos = [],
    isLoading: isReposLoading,
    isError: isReposError,
    error: reposError,
    refetch: refetchRepos,
  } = useRepositories()

  const isLoading = isStatsLoading || isReviewsLoading || isReposLoading
  const isError = isStatsError || isReviewsError || isReposError

  const getErrorMessage = () => {
    const err = statsError || reviewsError || reposError
    if (err instanceof ApiError) return err.getUserMessage()
    if (err instanceof Error) return err.message
    return "Failed to load dashboard metrics. Please try again."
  }

  const handleRetryAll = () => {
    refetchStats()
    refetchReviews()
    refetchRepos()
  }

  return (
    <AppShell>
      <PageHeader
        title="Command Center"
        description="Monitor live AI reviews, pending approvals, and architecture health."
      />

      {isLoading ? (
        <div className="space-y-8">
          <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4">
            {[1, 2, 3, 4].map((i) => (
              <CardSkeleton key={i} className="h-32" />
            ))}
          </div>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <CardSkeleton className="h-80" />
            <CardSkeleton className="h-80" />
          </div>
        </div>
      ) : isError || !stats ? (
        <div className="py-8">
          <ErrorState
            title="Unable to load command center"
            message={getErrorMessage()}
            onRetry={handleRetryAll}
          />
        </div>
      ) : (
        <>
          <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4 mb-8">
            <StatsCard
              title="Active Reviews"
              value={stats.activeReviews}
              icon={GitPullRequest}
              trend={{ value: 12, label: "vs last week", isPositive: true }}
            />
            <StatsCard
              title="Pending HITL"
              value={stats.hitlPending}
              icon={ShieldAlert}
              description="Requires human approval"
            />
            <div className="rounded-xl border border-white/[0.08] bg-card/60 backdrop-blur-md p-6 shadow-[inset_0_1px_0_0_rgba(255,255,255,0.03)] hover:border-white/[0.12] transition-colors flex flex-col justify-between">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-sm font-medium text-muted-foreground">Avg ACS Score</h3>
                <Activity className="h-4 w-4 text-muted-foreground" />
              </div>
              <div className="flex items-center justify-between">
                <AnimatedAcsScore score={stats.avgAcsScore} />
                <AcsScoreRing score={stats.avgAcsScore} size={48} strokeWidth={4} />
              </div>
            </div>
            <StatsCard
              title="Issues Prevented"
              value={stats.issuesFound}
              icon={Code2}
              trend={{ value: 8, label: "vs last week", isPositive: true }}
            />
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Recent Reviews */}
            <div className="border border-white/[0.08] bg-card/60 backdrop-blur-md rounded-xl overflow-hidden shadow-[inset_0_1px_0_0_rgba(255,255,255,0.03)] flex flex-col">
              <div className="px-4 py-3.5 border-b border-white/[0.06] bg-white/[0.02] flex items-center justify-between min-h-[44px]">
                <h3 className="text-sm font-semibold text-foreground">Recent Reviews</h3>
                <Link
                  href="/reviews"
                  className="text-xs font-semibold text-primary hover:text-primary/80 flex items-center gap-1 min-h-[44px] px-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary rounded-md"
                >
                  <span>View all</span>
                  <ArrowRight className="h-3.5 w-3.5" />
                </Link>
              </div>
              <div className="flex-1 overflow-auto">
                {reviews.length > 0 ? (
                  <ul className="divide-y divide-white/[0.04]">
                    {reviews.slice(0, 5).map((review) => (
                      <li key={review.id}>
                        <Link
                          href={`/reviews/${review.id}`}
                          className="block px-4 py-3 hover:bg-white/[0.03] transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-inset"
                        >
                          <div className="flex items-center justify-between gap-4">
                            <div className="flex flex-col gap-0.5 min-w-0">
                              <div className="flex items-center gap-2">
                                <span className="text-sm font-medium text-foreground truncate">
                                  {review.repoName}
                                </span>
                                <span className="text-[10px] font-mono text-muted-foreground">
                                  #{review.pullRequestNumber}
                                </span>
                              </div>
                              <p className="text-xs text-muted-foreground truncate">{review.title}</p>
                            </div>
                            <div className="flex items-center gap-3 shrink-0">
                              <SeverityBadge level={review.severity} />
                              <span className="text-xs text-muted-foreground whitespace-nowrap">
                                {new Date(review.createdAt).toLocaleTimeString([], {
                                  hour: "2-digit",
                                  minute: "2-digit",
                                })}
                              </span>
                            </div>
                          </div>
                        </Link>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <div className="p-8 text-center text-xs text-muted-foreground">
                    No recent reviews available.
                  </div>
                )}
              </div>
            </div>

            {/* Repository Health */}
            <div className="border border-white/[0.08] bg-card/60 backdrop-blur-md rounded-xl overflow-hidden shadow-[inset_0_1px_0_0_rgba(255,255,255,0.03)] flex flex-col">
              <div className="px-4 py-3.5 border-b border-white/[0.06] bg-white/[0.02] flex items-center justify-between min-h-[44px]">
                <h3 className="text-sm font-semibold text-foreground">Repository Health (ACS)</h3>
                <Link
                  href="/repos"
                  className="text-xs font-semibold text-primary hover:text-primary/80 flex items-center gap-1 min-h-[44px] px-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary rounded-md"
                >
                  <span>View all</span>
                  <ArrowRight className="h-3.5 w-3.5" />
                </Link>
              </div>
              <div className="flex-1 overflow-auto">
                {repos.length > 0 ? (
                  <ul className="divide-y divide-white/[0.04]">
                    {repos.slice(0, 5).map((repo) => (
                      <li key={repo.id} className="px-4 py-3 hover:bg-white/[0.03] transition-colors">
                        <div className="flex items-center justify-between gap-4">
                          <div className="flex flex-col gap-0.5 min-w-0">
                            <span className="text-sm font-medium text-foreground truncate">
                              {repo.name}
                            </span>
                            <span className="text-xs text-muted-foreground truncate">
                              {repo.owner}
                            </span>
                          </div>
                          <div className="flex items-center gap-4 shrink-0">
                            <AcsScoreRing score={repo.acsScore} size={36} strokeWidth={3} />
                          </div>
                        </div>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <div className="p-8 text-center text-xs text-muted-foreground">
                    No repositories connected.
                  </div>
                )}
              </div>
            </div>
          </div>
        </>
      )}
    </AppShell>
  )
}
