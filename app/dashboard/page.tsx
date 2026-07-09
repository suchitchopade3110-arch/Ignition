import { Metadata } from "next"
import { AppShell } from "@/components/app-shell"
import { PageHeader } from "@/components/page-header"
import { StatsCard } from "@/components/stats-card"
import { Activity, ShieldAlert, GitPullRequest, Code2 } from "lucide-react"
import { apiClient } from "@/lib/api-client"
import { AcsScoreRing } from "@/components/acs-score-ring"
import { SeverityBadge } from "@/components/severity-badge"
import { AnimatedAcsScore } from "@/components/animated-acs-score"

export const metadata: Metadata = {
  title: "Dashboard | Ignition",
  description: "Overview of AI Code Reviews and Repository Health",
}

export default async function DashboardPage() {
  const [stats, reviews, repos] = await Promise.all([
    apiClient.getDashboardStats(),
    apiClient.getReviews(),
    apiClient.getRepositories(),
  ])

  return (
    <AppShell>
      <PageHeader 
        title="Command Center" 
        description="Monitor live AI reviews, pending approvals, and architecture health." 
      />

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
        <div className="rounded-xl border border-border bg-card p-6 shadow-sm flex flex-col justify-between">
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

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Recent Reviews */}
        <div className="rounded-xl border border-border bg-card shadow-sm flex flex-col">
          <div className="px-6 py-5 border-b border-border">
            <h3 className="text-base font-semibold text-foreground">Recent Reviews</h3>
          </div>
          <div className="flex-1 p-0 overflow-auto">
            <ul className="divide-y divide-border">
              {reviews.slice(0, 4).map((review) => (
                <li key={review.id} className="p-6 hover:bg-secondary/30 transition-colors">
                  <div className="flex items-center justify-between">
                    <div className="flex flex-col gap-1">
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-medium text-foreground">{review.repoName}</span>
                        <span className="text-xs text-muted-foreground">#{review.pullRequestNumber}</span>
                      </div>
                      <p className="text-sm text-muted-foreground line-clamp-1">{review.title}</p>
                    </div>
                    <div className="flex items-center gap-3">
                      <SeverityBadge level={review.severity} />
                      <span className="text-xs text-muted-foreground whitespace-nowrap">
                        {new Date(review.createdAt).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                      </span>
                    </div>
                  </div>
                </li>
              ))}
            </ul>
          </div>
        </div>

        {/* Repository Health */}
        <div className="rounded-xl border border-border bg-card shadow-sm flex flex-col">
          <div className="px-6 py-5 border-b border-border">
            <h3 className="text-base font-semibold text-foreground">Repository Health (ACS)</h3>
          </div>
          <div className="flex-1 p-0 overflow-auto">
            <ul className="divide-y divide-border">
              {repos.slice(0, 4).map((repo) => (
                <li key={repo.id} className="p-6 hover:bg-secondary/30 transition-colors">
                  <div className="flex items-center justify-between">
                    <div className="flex flex-col gap-1">
                      <span className="text-sm font-medium text-foreground">{repo.name}</span>
                      <span className="text-xs text-muted-foreground">{repo.owner}</span>
                    </div>
                    <div className="flex items-center gap-4">
                      <AcsScoreRing score={repo.acsScore} size={40} strokeWidth={3} />
                    </div>
                  </div>
                </li>
              ))}
            </ul>
          </div>
        </div>
      </div>
    </AppShell>
  )
}
