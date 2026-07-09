"use client"

import { useEffect, useState } from "react"
import { AppShell } from "@/components/app-shell"
import { PageHeader } from "@/components/page-header"
import { SearchInput } from "@/components/search-input"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/table"
import { Pagination } from "@/components/pagination"
import { AcsScoreRing } from "@/components/acs-score-ring"
import { apiClient } from "@/lib/api-client"
import { Repository } from "@/lib/types"
import { TableSkeleton } from "@/components/loading-skeleton"
import { Settings, ExternalLink } from "lucide-react"

export default function RepositoriesPage() {
  const [repos, setRepos] = useState<Repository[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState("")
  const [page, setPage] = useState(1)

  useEffect(() => {
    async function load() {
      setLoading(true)
      try {
        const data = await apiClient.getRepositories()
        setRepos(data)
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [])

  const filteredRepos = repos.filter(repo => 
    repo.name.toLowerCase().includes(search.toLowerCase()) || 
    repo.owner.toLowerCase().includes(search.toLowerCase())
  )

  const itemsPerPage = 10
  const totalPages = Math.ceil(filteredRepos.length / itemsPerPage) || 1
  const paginatedRepos = filteredRepos.slice((page - 1) * itemsPerPage, page * itemsPerPage)

  return (
    <AppShell>
      <PageHeader 
        title="Repositories" 
        description="Manage connected repositories and view Architecture Compliance Scores."
        action={
          <button className="inline-flex items-center justify-center rounded-md text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:opacity-50 disabled:pointer-events-none ring-offset-background bg-primary text-primary-foreground hover:bg-primary/90 h-10 py-2 px-4">
            Connect Repository
          </button>
        }
      />

      <div className="mb-6 flex items-center justify-between gap-4">
        <div className="w-full max-w-sm">
          <SearchInput 
            placeholder="Search repositories..." 
            value={search}
            onChange={(e) => {
              setSearch(e.target.value)
              setPage(1)
            }}
          />
        </div>
      </div>

      <div className="bg-card border border-border rounded-xl shadow-sm">
        {loading ? (
          <div className="p-6">
            <TableSkeleton rows={5} />
          </div>
        ) : (
          <>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-[300px]">Repository</TableHead>
                  <TableHead>Owner</TableHead>
                  <TableHead>Language</TableHead>
                  <TableHead className="text-right">ACS Score</TableHead>
                  <TableHead className="w-[100px]"></TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {paginatedRepos.length > 0 ? (
                  paginatedRepos.map((repo) => (
                    <TableRow key={repo.id}>
                      <TableCell className="font-medium text-foreground">
                        <div className="flex items-center gap-2">
                          <span>{repo.name}</span>
                        </div>
                      </TableCell>
                      <TableCell className="text-muted-foreground">{repo.owner}</TableCell>
                      <TableCell>
                        <span className="inline-flex items-center rounded-md bg-secondary px-2 py-1 text-xs font-medium text-secondary-foreground ring-1 ring-inset ring-border">
                          {repo.language}
                        </span>
                      </TableCell>
                      <TableCell className="text-right">
                        <div className="flex items-center justify-end">
                          <AcsScoreRing score={repo.acsScore} size={36} strokeWidth={3} />
                        </div>
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center justify-end gap-2">
                          <button className="text-muted-foreground hover:text-foreground transition-colors p-1 rounded-md hover:bg-secondary">
                            <ExternalLink className="h-4 w-4" />
                            <span className="sr-only">Open</span>
                          </button>
                          <button className="text-muted-foreground hover:text-foreground transition-colors p-1 rounded-md hover:bg-secondary">
                            <Settings className="h-4 w-4" />
                            <span className="sr-only">Settings</span>
                          </button>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))
                ) : (
                  <TableRow>
                    <TableCell colSpan={5} className="h-32 text-center text-muted-foreground">
                      No repositories found.
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
