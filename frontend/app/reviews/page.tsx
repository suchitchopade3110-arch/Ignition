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
import { Filter } from "lucide-react"

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

      <div className="mb-6 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
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
        <div className="flex items-center gap-2">
          {/* Mock Filters for Phase 2 UI */}
          <button className="inline-flex items-center gap-2 px-3 py-2 rounded-md border border-border bg-card text-sm font-medium text-foreground hover:bg-secondary/50 transition-colors">
            <Filter className="h-4 w-4" />
            Repository
          </button>
          <button className="inline-flex items-center gap-2 px-3 py-2 rounded-md border border-border bg-card text-sm font-medium text-foreground hover:bg-secondary/50 transition-colors">
            <Filter className="h-4 w-4" />
            Status
          </button>
        </div>
      </div>

      <div className="bg-card border border-border rounded-xl shadow-sm">
        {loading ? (
          <div className="p-6">
            <TableSkeleton rows={8} />
          </div>
        ) : (
          <>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-[300px]">Pull Request</TableHead>
                  <TableHead>Repository</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Highest Severity</TableHead>
                  <TableHead>Duration</TableHead>
                  <TableHead className="text-right">ACS</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {paginatedReviews.length > 0 ? (
                  paginatedReviews.map((review) => (
                    <TableRow 
                      key={review.id}
                      className="cursor-pointer"
                      onClick={() => router.push(`/reviews/${review.id}`)}
                    >
                      <TableCell>
                        <div className="flex flex-col gap-1">
                          <span className="font-medium text-foreground line-clamp-1">{review.title}</span>
                          <span className="text-xs text-muted-foreground">#{review.pullRequestNumber} • {new Date(review.createdAt).toLocaleDateString()}</span>
                        </div>
                      </TableCell>
                      <TableCell className="text-muted-foreground font-medium">
                        {review.repoName}
                      </TableCell>
                      <TableCell>
                        <StatusBadge status={review.status} />
                      </TableCell>
                      <TableCell>
                        <SeverityBadge level={review.severity} />
                      </TableCell>
                      <TableCell className="text-muted-foreground text-sm">
                        {review.duration || "---"}
                      </TableCell>
                      <TableCell className="text-right">
                        <div className="flex items-center justify-end">
                          {review.acsScore !== undefined ? (
                            <AcsScoreRing score={review.acsScore} size={36} strokeWidth={3} />
                          ) : (
                            <span className="text-muted-foreground text-xs">N/A</span>
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
              className="rounded-t-none border-x-0 border-b-0"
            />
          </>
        )}
      </div>
    </AppShell>
  )
}
