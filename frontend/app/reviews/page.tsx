"use client"

import { useEffect, useState } from "react"
import { useRouter } from "next/navigation"
import { AppShell } from "@/components/app-shell"
import { PageHeader } from "@/components/page-header"
import { SearchInput } from "@/components/search-input"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/table"
import { Pagination } from "@/components/pagination"
import { AcsScoreRing } from "@/components/acs-score-ring"
import { apiClient } from "@/lib/api-client"
import { Review } from "@/lib/types"
import { TableSkeleton } from "@/components/loading-skeleton"
import { SeverityBadge } from "@/components/severity-badge"
import { StatusBadge } from "@/components/status-badge"
import { Filter, Calendar, Clock as ClockIcon } from "lucide-react"

export default function ReviewsPage() {
  const router = useRouter()
  const [reviews, setReviews] = useState<Review[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState("")
  const [page, setPage] = useState(1)

  useEffect(() => {
    async function load() {
      setLoading(true)
      try {
        const data = await apiClient.getReviews()
        setReviews(data)
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [])

  const filteredReviews = reviews.filter(rev => 
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
        <div className="flex items-center gap-2 self-end sm:self-auto">
          {/* Mock Filters for Phase 2 UI */}
          <button className="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg border border-[#22262B] bg-[#14171A] text-xs font-semibold text-muted-foreground hover:bg-[#1C1F22] hover:text-foreground transition-all">
            <Filter className="h-3.5 w-3.5" />
            Repository
          </button>
          <button className="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg border border-[#22262B] bg-[#14171A] text-xs font-semibold text-muted-foreground hover:bg-[#1C1F22] hover:text-foreground transition-all">
            <Filter className="h-3.5 w-3.5" />
            Status
          </button>
        </div>
      </div>

      <div className="bg-[#14171A] rounded-xl border border-[#22262B] shadow-lg shadow-black/40 overflow-hidden">
        {loading ? (
          <div className="p-6">
            <TableSkeleton rows={8} />
          </div>
        ) : (
          <>
            <Table className="border-0 rounded-none">
              <TableHeader className="bg-[#0B0D0F]">
                <TableRow className="border-b border-[#22262B] hover:bg-transparent">
                  <TableHead className="w-[380px] text-xs font-bold uppercase tracking-wider text-muted-foreground py-3">Pull Request</TableHead>
                  <TableHead className="text-xs font-bold uppercase tracking-wider text-muted-foreground py-3">Repository</TableHead>
                  <TableHead className="text-xs font-bold uppercase tracking-wider text-muted-foreground py-3">Status</TableHead>
                  <TableHead className="text-xs font-bold uppercase tracking-wider text-muted-foreground py-3">Highest Severity</TableHead>
                  <TableHead className="text-xs font-bold uppercase tracking-wider text-muted-foreground py-3">Duration</TableHead>
                  <TableHead className="text-right text-xs font-bold uppercase tracking-wider text-muted-foreground py-3">ACS</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {paginatedReviews.length > 0 ? (
                  paginatedReviews.map((review) => (
                    <TableRow 
                      key={review.id}
                      className="cursor-pointer border-b border-[#22262B] hover:bg-[#1C1F22] transition-colors"
                      onClick={() => router.push(`/reviews/${review.id}`)}
                    >
                      <TableCell className="py-4">
                        <div className="flex flex-col gap-1">
                          <span className="font-semibold text-foreground line-clamp-1 hover:text-primary transition-colors">{review.title}</span>
                          <div className="flex items-center gap-2 text-xs text-muted-foreground font-mono">
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
                      <TableCell className="text-muted-foreground text-xs font-mono">
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
                        <div className="flex items-center justify-end font-mono">
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
                    <TableCell colSpan={6} className="h-32 text-center text-muted-foreground">
                      No reviews match your filters.
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
            <Pagination 
              currentPage={page} 
              totalPages={totalPages} 
              onPageChange={setPage} 
              className="rounded-t-none border-x-0 border-b-0 border-t border-[#22262B] bg-[#0B0D0F]/45"
            />
          </>
        )}
      </div>
    </AppShell>
  )
}

