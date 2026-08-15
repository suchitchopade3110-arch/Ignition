"use client"

import { useReview } from "@/hooks/queries/use-review"
import { ReviewDetail } from "@/types"
import { StatusBadge } from "@/components/ui/status-badge"
import { SeverityBadge } from "@/components/ui/severity-badge"
import { AnimatedAcsScore } from "@/components/ui/animated-acs-score"
import { AcsScoreRing } from "@/components/ui/acs-score-ring"
import { RegressionBanner } from "./regression-banner"
import { LiveReviewStream } from "./live-review-stream"
import { DiffViewer } from "./diff-viewer"
import { MarkdownPreview } from "./markdown-preview"
import { GitBranch, Clock, FileDiff, Code, Calendar } from "lucide-react"

export function ReviewDetailView({
  reviewId,
  initialData,
}: {
  reviewId: string
  initialData?: ReviewDetail
}) {
  const { data: review = initialData } = useReview(reviewId, initialData)

  if (!review) return null

  const isRunning = review.status === "running" || review.status === "queued"

  return (
    <>
      {/* Header */}
      <div className="mb-8 flex flex-col gap-4 md:flex-row md:items-start md:justify-between border-b border-border pb-6">
        <div className="space-y-2 min-w-0">
          <div className="flex flex-wrap items-center gap-3">
            <h1 className="text-2xl font-bold tracking-tight text-foreground truncate">{review.title}</h1>
            <StatusBadge status={review.status} />
          </div>
          <div className="flex flex-wrap items-center gap-x-4 gap-y-2 text-xs text-muted-foreground mt-2 font-mono">
            <div className="flex items-center gap-1.5 bg-card px-2.5 py-1 rounded-md border border-border">
              <span className="font-semibold text-foreground">{review.repoName}</span>
              <span className="text-muted-foreground/60">#{review.pullRequestNumber}</span>
            </div>
            <div className="flex items-center gap-1.5 bg-card px-2.5 py-1 rounded-md border border-border">
              <GitBranch className="h-3.5 w-3.5 text-primary" />
              <span>{review.branch}</span>
            </div>
            <div className="flex items-center gap-1.5 bg-card px-2.5 py-1 rounded-md border border-border">
              <Code className="h-3.5 w-3.5 text-muted-foreground" />
              <span className="tabular-nums">{review.commitSha.substring(0, 7)}</span>
            </div>
            <div className="flex items-center gap-1.5 bg-card px-2.5 py-1 rounded-md border border-border">
              <Calendar className="h-3.5 w-3.5 text-muted-foreground" />
              <span>{new Date(review.createdAt).toLocaleString()}</span>
            </div>
          </div>
        </div>
        <div className="flex items-center gap-3 shrink-0">
          <a
            href={`https://github.com/${review.repoName}/pull/${review.pullRequestNumber}`}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center justify-center min-h-[44px] rounded-lg border border-border bg-card px-4 py-2 text-xs font-semibold text-foreground hover:bg-secondary/60 hover:text-primary transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
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

      {/* Review Summary Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-10">
        <div className="rounded-xl border border-border bg-card p-5 flex items-center justify-between hover:border-primary/30 transition-colors group">
          <div>
            <p className="text-xs font-bold uppercase tracking-wider text-muted-foreground mb-1">Architecture Score</p>
            <AnimatedAcsScore score={review.acsScore || 0} />
          </div>
          <div>
            <AcsScoreRing score={review.acsScore || 0} size={52} strokeWidth={4} />
          </div>
        </div>
        <div className="rounded-xl border border-border bg-card p-5 flex flex-col justify-between hover:border-border transition-colors">
          <p className="text-xs font-bold uppercase tracking-wider text-muted-foreground mb-3">Overall Severity</p>
          <div>
            <SeverityBadge level={review.severity} className="text-xs px-3 py-1" />
          </div>
        </div>
        <div className="rounded-xl border border-border bg-card p-5 flex flex-col justify-between hover:border-border transition-colors">
          <div className="flex items-center justify-between mb-3">
            <p className="text-xs font-bold uppercase tracking-wider text-muted-foreground">Changes</p>
            <FileDiff className="h-4 w-4 text-muted-foreground" />
          </div>
          <div className="flex items-center gap-3 text-sm font-semibold font-mono tabular-nums">
            <span className="text-foreground">{review.filesChanged} files</span>
            <span className="text-success">+{review.linesAdded}</span>
            <span className="text-critical">-{review.linesDeleted}</span>
          </div>
        </div>
        <div className="rounded-xl border border-border bg-card p-5 flex flex-col justify-between hover:border-border transition-colors">
          <div className="flex items-center justify-between mb-3">
            <p className="text-xs font-bold uppercase tracking-wider text-muted-foreground">Duration</p>
            <Clock className="h-4 w-4 text-muted-foreground" />
          </div>
          <p className="text-xl font-bold text-foreground font-mono tabular-nums">
            {isRunning ? (
              <span className="text-primary flex items-center gap-1.5 text-sm uppercase tracking-wider">
                <span className="relative flex h-2 w-2">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-primary opacity-75"></span>
                  <span className="relative inline-flex rounded-full h-2 w-2 bg-primary"></span>
                </span>
                Running...
              </span>
            ) : (
              review.duration || "N/A"
            )}
          </p>
        </div>
      </div>

      {/* Main Content Area */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Left Column (Timeline & Findings via SSE wrapper) */}
        <div className="lg:col-span-2 space-y-12 min-w-0">
          <LiveReviewStream initialData={review} />

          {/* Diff Viewer section */}
          {review.diffs && review.diffs.length > 0 && (
            <section className="min-w-0">
              <h2 className="text-lg font-semibold text-foreground mb-6">Code Changes</h2>
              <div className="space-y-6 min-w-0">
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

        {/* Right Column (Final Output Preview) */}
        <div className="space-y-8 min-w-0">
          <section className="min-w-0">
            <h2 className="text-sm font-semibold text-foreground uppercase tracking-wider mb-4">Final Output</h2>
            <MarkdownPreview content={review.githubCommentPreview} />
          </section>
        </div>
      </div>
    </>
  )
}
