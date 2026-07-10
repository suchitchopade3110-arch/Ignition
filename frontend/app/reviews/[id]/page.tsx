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
      <div className="mb-8 flex flex-col gap-4 md:flex-row md:items-start md:justify-between border-b border-[#22262B] pb-6">
        <div className="space-y-2">
          <div className="flex flex-wrap items-center gap-3">
            <h1 className="text-2xl font-bold tracking-tight text-foreground">{review.title}</h1>
            <StatusBadge status={review.status} />
          </div>
          <div className="flex flex-wrap items-center gap-x-4 gap-y-2 text-xs text-muted-foreground mt-2 font-mono">
            <div className="flex items-center gap-1.5 bg-[#14171A] px-2.5 py-1 rounded-md border border-[#22262B]">
              <span className="font-semibold text-foreground">{review.repoName}</span>
              <span className="text-muted-foreground/60">#{review.pullRequestNumber}</span>
            </div>
            <div className="flex items-center gap-1.5 bg-[#14171A] px-2.5 py-1 rounded-md border border-[#22262B]">
              <GitBranch className="h-3.5 w-3.5 text-primary" />
              <span>{review.branch}</span>
            </div>
            <div className="flex items-center gap-1.5 bg-[#14171A] px-2.5 py-1 rounded-md border border-[#22262B]">
              <Code className="h-3.5 w-3.5 text-muted-foreground" />
              <span>{review.commitSha.substring(0, 7)}</span>
            </div>
            <div className="flex items-center gap-1.5 bg-[#14171A] px-2.5 py-1 rounded-md border border-[#22262B]">
              <Calendar className="h-3.5 w-3.5 text-muted-foreground" />
              <span>{new Date(review.createdAt).toLocaleString()}</span>
            </div>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <a
            href={`https://github.com/${review.repoName}/pull/${review.pullRequestNumber}`}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center justify-center rounded-lg border border-[#22262B] bg-[#14171A] px-4 py-2 text-xs font-semibold text-foreground hover:bg-[#1C1F22] hover:text-primary transition-all shadow-md shadow-black/20"
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
        <div className="rounded-xl border border-[#22262B] bg-[#14171A] p-5 flex items-center justify-between shadow-lg shadow-black/20 hover:border-[#E85D2F]/30 transition-all group">
          <div>
            <p className="text-xs font-bold uppercase tracking-wider text-muted-foreground mb-1">Architecture Score</p>
            <AnimatedAcsScore score={review.acsScore || 0} />
          </div>
          <div className="group-hover:scale-105 transition-transform">
            <AcsScoreRing score={review.acsScore || 0} size={52} strokeWidth={4} />
          </div>
        </div>
        <div className="rounded-xl border border-[#22262B] bg-[#14171A] p-5 shadow-lg shadow-black/20 flex flex-col justify-between hover:border-[#22262B]/80 transition-all">
          <p className="text-xs font-bold uppercase tracking-wider text-muted-foreground mb-3">Overall Severity</p>
          <div>
            <SeverityBadge level={review.severity} className="text-xs px-3 py-1" />
          </div>
        </div>
        <div className="rounded-xl border border-[#22262B] bg-[#14171A] p-5 shadow-lg shadow-black/20 flex flex-col justify-between hover:border-[#22262B]/80 transition-all">
          <div className="flex items-center justify-between mb-3">
            <p className="text-xs font-bold uppercase tracking-wider text-muted-foreground">Changes</p>
            <FileDiff className="h-4 w-4 text-muted-foreground" />
          </div>
          <div className="flex items-center gap-3 text-sm font-semibold font-mono">
            <span className="text-foreground">{review.filesChanged} files</span>
            <span className="text-success">+{review.linesAdded}</span>
            <span className="text-critical">-{review.linesDeleted}</span>
          </div>
        </div>
        <div className="rounded-xl border border-[#22262B] bg-[#14171A] p-5 shadow-lg shadow-black/20 flex flex-col justify-between hover:border-[#22262B]/80 transition-all">
          <div className="flex items-center justify-between mb-3">
            <p className="text-xs font-bold uppercase tracking-wider text-muted-foreground">Duration</p>
            <Clock className="h-4 w-4 text-muted-foreground" />
          </div>
          <p className="text-xl font-bold text-foreground font-mono">
            {isRunning ? (
              <span className="text-primary animate-pulse flex items-center gap-1.5 text-sm uppercase tracking-wider">
                <span className="relative flex h-2 w-2">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-primary opacity-75"></span>
                  <span className="relative inline-flex rounded-full h-2 w-2 bg-primary"></span>
                </span>
                Running...
              </span>
            ) : review.duration || "N/A"}
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
