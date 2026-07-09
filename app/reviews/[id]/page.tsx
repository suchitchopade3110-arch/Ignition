import { Metadata } from "next"
import { notFound } from "next/navigation"
import { AppShell } from "@/components/app-shell"
import { StatusBadge } from "@/components/status-badge"
import { SeverityBadge } from "@/components/severity-badge"
import { AnimatedAcsScore } from "@/components/animated-acs-score"
import { AcsScoreRing } from "@/components/acs-score-ring"
import { RegressionBanner } from "@/components/regression-banner"
import { LiveReviewStream } from "@/components/live-review-stream"
import { DiffViewer } from "@/components/diff-viewer"
import { MarkdownPreview } from "@/components/markdown-preview"
import { apiClient } from "@/lib/api-client"
import { GitBranch, Clock, FileDiff, Code, Calendar } from "lucide-react"

export const metadata: Metadata = {
  title: "Review Details | Ignition",
  description: "View AI Code Review details and findings",
}

export default async function ReviewDetailPage(props: { params: Promise<{ id: string }> }) {
  const params = await props.params;
  const review = await apiClient.getReview(params.id)

  if (!review) {
    notFound()
  }

  const isRunning = review.status === "running" || review.status === "queued"

  return (
    <AppShell>
      {/* Header */}
      <div className="mb-8 flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
        <div className="space-y-1">
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold tracking-tight text-foreground">{review.title}</h1>
            <StatusBadge status={review.status} />
          </div>
          <div className="flex flex-wrap items-center gap-x-4 gap-y-2 text-sm text-muted-foreground mt-2">
            <div className="flex items-center gap-1.5">
              <span className="font-medium text-foreground">{review.repoName}</span>
              <span>#{review.pullRequestNumber}</span>
            </div>
            <div className="flex items-center gap-1.5">
              <GitBranch className="h-4 w-4" />
              <span>{review.branch}</span>
            </div>
            <div className="flex items-center gap-1.5">
              <Code className="h-4 w-4" />
              <span className="font-mono">{review.commitSha.substring(0, 7)}</span>
            </div>
            <div className="flex items-center gap-1.5">
              <Calendar className="h-4 w-4" />
              <span>{new Date(review.createdAt).toLocaleString()}</span>
            </div>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <a
            href={`https://github.com/${review.repoName}/pull/${review.pullRequestNumber}`}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center justify-center rounded-md border border-border bg-card px-4 py-2 text-sm font-medium text-foreground hover:bg-secondary transition-colors"
          >
            View on GitHub
          </a>
        </div>
      </div>

      {/* Regression Alert (if applicable) */}
      {review.regression?.isRegression && (
        <div className="mb-8">
          <RegressionBanner regression={review.regression} />
        </div>
      )}

      {/* Review Summary Card */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-10">
        <div className="rounded-xl border border-border bg-card p-5 flex items-center justify-between">
          <div>
            <p className="text-sm font-medium text-muted-foreground mb-1">Architecture Score</p>
            <AnimatedAcsScore score={review.acsScore || 0} />
          </div>
          <AcsScoreRing score={review.acsScore || 0} size={52} strokeWidth={4} />
        </div>
        <div className="rounded-xl border border-border bg-card p-5">
          <p className="text-sm font-medium text-muted-foreground mb-3">Overall Severity</p>
          <SeverityBadge level={review.severity} className="text-sm px-3 py-1" />
        </div>
        <div className="rounded-xl border border-border bg-card p-5">
          <div className="flex items-center justify-between mb-3">
            <p className="text-sm font-medium text-muted-foreground">Changes</p>
            <FileDiff className="h-4 w-4 text-muted-foreground" />
          </div>
          <div className="flex items-center gap-3 text-sm font-medium">
            <span className="text-foreground">{review.filesChanged} files</span>
            <span className="text-success">+{review.linesAdded}</span>
            <span className="text-critical">-{review.linesDeleted}</span>
          </div>
        </div>
        <div className="rounded-xl border border-border bg-card p-5">
          <div className="flex items-center justify-between mb-3">
            <p className="text-sm font-medium text-muted-foreground">Duration</p>
            <Clock className="h-4 w-4 text-muted-foreground" />
          </div>
          <p className="text-2xl font-bold text-foreground">
            {isRunning ? "Running..." : review.duration || "N/A"}
          </p>
        </div>
      </div>

      {/* Main Content Area */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        
        {/* Left Column (Timeline & Findings via SSE wrapper) */}
        <div className="lg:col-span-2 space-y-12">
          <LiveReviewStream initialData={review} />

          {/* Diff Viewer section */}
          {review.diffs && review.diffs.length > 0 && (
            <section>
              <h2 className="text-lg font-semibold text-foreground mb-6">Code Changes</h2>
              <div className="space-y-6">
                {review.diffs.map((diff, idx) => (
                  <DiffViewer 
                    key={idx}
                    file={diff.file}
                    additions={diff.additions}
                    deletions={diff.deletions}
                    content={diff.content}
                  />
                ))}
              </div>
            </section>
          )}
        </div>

        {/* Right Column (Sidebar components) */}
        <div className="space-y-8">
          <section>
            <h2 className="text-sm font-semibold text-foreground uppercase tracking-wider mb-4">Final Output</h2>
            <MarkdownPreview content={review.githubCommentPreview} />
          </section>
        </div>
        
      </div>
    </AppShell>
  )
}
