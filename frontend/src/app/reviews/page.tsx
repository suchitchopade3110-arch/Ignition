"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import { AppShell } from "@/components/layout/app-shell"
import { PageHeader } from "@/components/layout/page-header"
import { SearchInput } from "@/components/ui/search-input"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Pagination } from "@/components/ui/pagination"
import { AcsScoreRing } from "@/components/ui/acs-score-ring"
import { TableSkeleton } from "@/components/ui/loading-skeleton"
import { SeverityBadge } from "@/components/ui/severity-badge"
import { StatusBadge } from "@/components/ui/status-badge"
import { Calendar, Clock as ClockIcon, MessageSquare, ChevronRight } from "lucide-react"
import { EmptyState } from "@/components/ui/empty-state"
import { ErrorState } from "@/components/ui/error-state"
import { ApiError } from "@/lib/errors"
import { useReviews } from "@/hooks/queries/use-reviews"

export default function ReviewsPage() {
  const router = useRouter()
  const { data: reviews = [], isLoading, isError, error, refetch } = useReviews()
  const [search, setSearch] = useState("")
  const [page, setPage] = useState(1)

  const getErrorMessage = () => {
    if (error instanceof ApiError) return error.getUserMessage()
    if (error instanceof Error) return error.message
    return "Failed to load code reviews. Please try again."
  }

  const filteredReviews = reviews.filter(
    (rev) =>
      rev.repoName.toLowerCase().includes(search.toLowerCase()) ||
      rev.title.toLowerCase().includes(search.toLowerCase())
  )

  const itemsPerPage = 10
  const totalPages = Math.ceil(filteredReviews.length / itemsPerPage) || 1
  const paginatedReviews = filteredReviews.slice((page - 1) * itemsPerPage, page * itemsPerPage)

  return (
    <AppShell>
      <PageHeader
        title="Code Reviews"
        description="Monitor ongoing and completed autonomous AI code reviews across all repositories."
      />

      <div className="mb-6 flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-4">
        <div className="w-full max-w-md">
          <SearchInput
            placeholder="Search by repository or PR title..."
            value={search}
            onChange={(e) => {
              setSearch(e.target.value)
              setPage(1)
            }}
          />
        </div>
      </div>

      <div className="bg-card rounded-xl border border-white/[0.08] overflow-hidden shadow-[inset_0_1px_0_0_rgba(255,255,255,0.03)]">
        {isLoading ? (
          <div className="p-6">
            <TableSkeleton rows={8} />
          </div>
        ) : isError ? (
          <div className="p-6">
            <ErrorState
              title="Unable to load code reviews"
              message={getErrorMessage()}
              onRetry={() => refetch()}
            />
          </div>
        ) : reviews.length === 0 ? (
          <div className="p-6">
            <EmptyState
              icon={MessageSquare}
              title="No code reviews yet"
              description="Open a pull request on a connected repository to initiate autonomous multi-agent analysis."
            />
          </div>
        ) : (
          <>
            {/* Desktop View: Semantic Data Table */}
            <div className="hidden sm:block overflow-x-auto">
              <Table className="border-0 rounded-none">
                <TableHeader className="bg-white/[0.02]">
                  <TableRow className="border-b border-white/[0.06] hover:bg-transparent">
                    <TableHead className="w-[380px] text-xs font-bold uppercase tracking-wider text-muted-foreground py-3">
                      Pull Request
                    </TableHead>
                    <TableHead className="text-xs font-bold uppercase tracking-wider text-muted-foreground py-3">
                      Repository
                    </TableHead>
                    <TableHead className="text-xs font-bold uppercase tracking-wider text-muted-foreground py-3">
                      Status
                    </TableHead>
                    <TableHead className="text-xs font-bold uppercase tracking-wider text-muted-foreground py-3">
                      Highest Severity
                    </TableHead>
                    <TableHead className="text-xs font-bold uppercase tracking-wider text-muted-foreground py-3">
                      Duration
                    </TableHead>
                    <TableHead className="text-right text-xs font-bold uppercase tracking-wider text-muted-foreground py-3">
                      ACS
                    </TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {paginatedReviews.length > 0 ? (
                    paginatedReviews.map((review) => (
                      <TableRow
                        key={review.id}
                        tabIndex={0}
                        role="link"
                        aria-label={`View review for ${review.title}`}
                        className="cursor-pointer border-b border-white/[0.04] hover:bg-white/[0.02] transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-inset"
                        onClick={() => router.push(`/reviews/${review.id}`)}
                        onKeyDown={(e) => {
                          if (e.key === "Enter" || e.key === " ") {
                            e.preventDefault()
                            router.push(`/reviews/${review.id}`)
                          }
                        }}
                      >
                        <TableCell className="py-4">
                          <div className="flex flex-col gap-1">
                            <span className="font-semibold text-foreground line-clamp-1 hover:text-primary transition-colors">
                              {review.title}
                            </span>
                            <div className="flex items-center gap-2 text-xs text-muted-foreground font-mono tabular-nums">
                              <span>#{review.pullRequestNumber}</span>
                              <span>•</span>
                              <span className="flex items-center gap-1">
                                <Calendar className="h-3 w-3" />
                                {new Date(review.createdAt).toLocaleDateString()}
                              </span>
                            </div>
                          </div>
                        </TableCell>
                        <TableCell className="font-mono text-xs text-muted-foreground">
                          {review.repoName}
                        </TableCell>
                        <TableCell>
                          <StatusBadge status={review.status} />
                        </TableCell>
                        <TableCell>
                          <SeverityBadge level={review.severity} />
                        </TableCell>
                        <TableCell className="text-muted-foreground text-xs font-mono tabular-nums">
                          {review.duration ? (
                            <span className="flex items-center gap-1">
                              <ClockIcon className="h-3 w-3" />
                              {review.duration}
                            </span>
                          ) : (
                            <span className="text-muted-foreground/40">—</span>
                          )}
                        </TableCell>
                        <TableCell className="text-right py-4">
                          <div className="flex items-center justify-end font-mono tabular-nums">
                            {review.acsScore !== undefined ? (
                              <AcsScoreRing score={review.acsScore} size={32} strokeWidth={3} />
                            ) : (
                              <span className="text-muted-foreground/40 text-xs">N/A</span>
                            )}
                          </div>
                        </TableCell>
                      </TableRow>
                    ))
                  ) : (
                    <TableRow>
                      <TableCell colSpan={6} className="h-32 text-center text-muted-foreground text-sm">
                        No reviews match your filters.
                      </TableCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>
            </div>

            {/* Mobile View: Stacked Interactive Review Cards (< sm) */}
            <div className="sm:hidden divide-y divide-white/[0.04]">
              {paginatedReviews.length > 0 ? (
                paginatedReviews.map((review) => (
                  <div
                    key={review.id}
                    tabIndex={0}
                    role="link"
                    aria-label={`View review for ${review.title}`}
                    onClick={() => router.push(`/reviews/${review.id}`)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter" || e.key === " ") {
                        e.preventDefault()
                        router.push(`/reviews/${review.id}`)
                      }
                    }}
                    className="p-4 space-y-3 hover:bg-white/[0.03] active:bg-white/[0.05] transition-colors cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-inset"
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div className="space-y-1 min-w-0 flex-1">
                        <span className="text-[11px] font-mono tabular-nums text-muted-foreground block truncate">
                          {review.repoName} #{review.pullRequestNumber}
                        </span>
                        <h3 className="font-semibold text-foreground text-sm line-clamp-2 hover:text-primary transition-colors">
                          {review.title}
                        </h3>
                      </div>
                      <div className="shrink-0 flex items-center gap-1.5 pt-0.5">
                        {review.acsScore !== undefined ? (
                          <AcsScoreRing score={review.acsScore} size={34} strokeWidth={3} />
                        ) : (
                          <span className="text-muted-foreground/40 text-xs font-mono">N/A</span>
                        )}
                        <ChevronRight className="h-4 w-4 text-muted-foreground/60" />
                      </div>
                    </div>

                    <div className="flex flex-wrap items-center justify-between gap-2 pt-1 border-t border-white/[0.04]">
                      <div className="flex items-center gap-2">
                        <StatusBadge status={review.status} />
                        <SeverityBadge level={review.severity} />
                      </div>
                      <div className="flex items-center gap-3 text-muted-foreground text-[11px] font-mono tabular-nums">
                        {review.duration && (
                          <span className="flex items-center gap-1">
                            <ClockIcon className="h-3 w-3" />
                            {review.duration}
                          </span>
                        )}
                        <span className="flex items-center gap-1">
                          <Calendar className="h-3 w-3" />
                          {new Date(review.createdAt).toLocaleDateString()}
                        </span>
                      </div>
                    </div>
                  </div>
                ))
              ) : (
                <div className="p-8 text-center text-xs text-muted-foreground">
                  No reviews match your filters.
                </div>
              )}
            </div>

            <Pagination
              currentPage={page}
              totalPages={totalPages}
              onPageChange={setPage}
              className="rounded-t-none border-x-0 border-b-0 border-t border-white/[0.06] bg-white/[0.02]"
            />
          </>
        )}
      </div>
    </AppShell>
  )
}
