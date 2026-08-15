"use client"

import { useState } from "react"
import { AppShell } from "@/components/layout/app-shell"
import { PageHeader } from "@/components/layout/page-header"
import { SearchInput } from "@/components/ui/search-input"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Pagination } from "@/components/ui/pagination"
import { AcsScoreRing } from "@/components/ui/acs-score-ring"
import { Repository, RepositorySettings } from "@/types"
import { TableSkeleton } from "@/components/ui/loading-skeleton"
import { Settings, ExternalLink, GitBranch } from "lucide-react"
import { RepositorySettingsDialog } from "@/components/repositories/repository-settings-dialog"
import { EmptyState } from "@/components/ui/empty-state"
import { ErrorState } from "@/components/ui/error-state"
import { ApiError } from "@/lib/errors"
import { useRepositories } from "@/hooks/queries/use-repositories"

export default function RepositoriesPage() {
  const { data: repos = [], isLoading, isError, error, refetch } = useRepositories()
  const [search, setSearch] = useState("")
  const [page, setPage] = useState(1)

  // Settings dialog state
  const [selectedRepo, setSelectedRepo] = useState<Repository | null>(null)
  const [settingsOpen, setSettingsOpen] = useState(false)
  const [repoSettings, setRepoSettings] = useState<RepositorySettings | undefined>(undefined)

  const handleOpenSettings = (repo: Repository) => {
    setSelectedRepo(repo)
    setSettingsOpen(true)
  }

  const handleCloseSettings = () => {
    setSettingsOpen(false)
    setSelectedRepo(null)
    setRepoSettings(undefined)
  }

  const getErrorMessage = () => {
    if (error instanceof ApiError) return error.getUserMessage()
    if (error instanceof Error) return error.message
    return "Failed to load repositories. Please try again."
  }

  const filteredRepos = repos.filter(
    (repo) =>
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
          <button
            type="button"
            className="inline-flex items-center justify-center min-h-[44px] rounded-full text-xs font-semibold transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 focus-visible:ring-offset-background bg-primary text-primary-foreground hover:bg-primary/90 py-2.5 px-5 shadow-[0_0_15px_rgba(255,69,0,0.15)]"
          >
            Connect Repository
          </button>
        }
      />

      <div className="mb-4 flex items-center justify-between gap-4">
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

      <div className="bg-card/60 backdrop-blur-md border border-white/[0.08] rounded-xl overflow-hidden shadow-[inset_0_1px_0_0_rgba(255,255,255,0.03)]">
        {isLoading ? (
          <div className="p-6">
            <TableSkeleton rows={5} />
          </div>
        ) : isError ? (
          <div className="p-6">
            <ErrorState
              title="Unable to load repositories"
              message={getErrorMessage()}
              onRetry={() => refetch()}
            />
          </div>
        ) : repos.length === 0 ? (
          <div className="p-6">
            <EmptyState
              icon={GitBranch}
              title="No repositories connected"
              description="Connect a GitHub repository to begin running autonomous AI code reviews."
              action={
                <button
                  type="button"
                  className="inline-flex items-center justify-center min-h-[44px] rounded-lg text-xs font-semibold bg-primary text-primary-foreground hover:bg-primary/90 px-4 py-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary shadow-[0_0_15px_rgba(255,69,0,0.2)]"
                >
                  Connect your first repository
                </button>
              }
            />
          </div>
        ) : (
          <>
            {/* Desktop View: Semantic Data Table */}
            <div className="hidden sm:block overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow className="bg-white/[0.02] border-b border-white/[0.06]">
                    <TableHead className="w-[300px] py-3 text-xs lowercase">repository</TableHead>
                    <TableHead className="py-3 text-xs lowercase">owner</TableHead>
                    <TableHead className="py-3 text-xs lowercase">language</TableHead>
                    <TableHead className="text-right py-3 text-xs lowercase">acs score</TableHead>
                    <TableHead className="w-[100px] py-3"></TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {paginatedRepos.length > 0 ? (
                    paginatedRepos.map((repo) => (
                      <TableRow key={repo.id} className="hover:bg-white/[0.02] border-b border-white/[0.04] transition-colors">
                        <TableCell className="font-semibold text-foreground py-3 text-sm">
                          <div className="flex items-center gap-2">
                            <span>{repo.name}</span>
                          </div>
                        </TableCell>
                        <TableCell className="text-muted-foreground py-3 text-xs">{repo.owner}</TableCell>
                        <TableCell className="py-3">
                          <span className="inline-flex items-center rounded bg-secondary/70 px-2 py-0.5 text-[10px] font-semibold text-secondary-foreground border border-white/[0.06]">
                            {repo.language.toLowerCase()}
                          </span>
                        </TableCell>
                        <TableCell className="text-right py-3">
                          <div className="flex items-center justify-end">
                            <AcsScoreRing score={repo.acsScore} size={30} strokeWidth={2.5} />
                          </div>
                        </TableCell>
                        <TableCell className="py-3">
                          <div className="flex items-center justify-end gap-1">
                            <button
                              type="button"
                              aria-label={`Open repository ${repo.name} externally`}
                              className="text-muted-foreground hover:text-foreground transition-colors p-2.5 rounded-lg hover:bg-white/[0.05] min-h-[44px] min-w-[44px] flex items-center justify-center focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
                            >
                              <ExternalLink className="h-4 w-4" />
                            </button>
                            <button
                              type="button"
                              onClick={() => handleOpenSettings(repo)}
                              aria-label={`Settings for ${repo.name}`}
                              className="text-muted-foreground hover:text-foreground transition-colors p-2.5 rounded-lg hover:bg-white/[0.05] min-h-[44px] min-w-[44px] flex items-center justify-center focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
                            >
                              <Settings className="h-4 w-4" />
                            </button>
                          </div>
                        </TableCell>
                      </TableRow>
                    ))
                  ) : (
                    <TableRow>
                      <TableCell colSpan={5} className="h-32 text-center text-muted-foreground text-sm">
                        No repositories match your search criteria.
                      </TableCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>
            </div>

            {/* Mobile View: Stacked Responsive Cards (< sm) */}
            <div className="sm:hidden divide-y divide-white/[0.04]">
              {paginatedRepos.length > 0 ? (
                paginatedRepos.map((repo) => (
                  <div key={repo.id} className="p-4 space-y-3 bg-transparent">
                    <div className="flex items-start justify-between gap-3">
                      <div className="space-y-1 min-w-0">
                        <h3 className="font-semibold text-foreground text-sm truncate">{repo.name}</h3>
                        <p className="text-xs text-muted-foreground truncate">{repo.owner}</p>
                      </div>
                      <div className="shrink-0 flex items-center gap-2">
                        <AcsScoreRing score={repo.acsScore} size={32} strokeWidth={3} />
                      </div>
                    </div>

                    <div className="flex items-center justify-between gap-2 pt-1">
                      <span className="inline-flex items-center rounded bg-secondary/70 px-2.5 py-1 text-[11px] font-semibold text-secondary-foreground border border-white/[0.06]">
                        {repo.language}
                      </span>
                      <div className="flex items-center gap-2">
                        <button
                          type="button"
                          aria-label={`Open repository ${repo.name} externally`}
                          className="text-muted-foreground hover:text-foreground p-2.5 rounded-lg border border-white/[0.08] bg-secondary/30 min-h-[44px] min-w-[44px] flex items-center justify-center focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
                        >
                          <ExternalLink className="h-4 w-4" />
                        </button>
                        <button
                          type="button"
                          onClick={() => handleOpenSettings(repo)}
                          aria-label={`Settings for ${repo.name}`}
                          className="text-muted-foreground hover:text-foreground p-2.5 rounded-lg border border-white/[0.08] bg-secondary/30 min-h-[44px] min-w-[44px] flex items-center justify-center focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
                        >
                          <Settings className="h-4 w-4" />
                        </button>
                      </div>
                    </div>
                  </div>
                ))
              ) : (
                <div className="p-8 text-center text-xs text-muted-foreground">
                  No repositories match your search criteria.
                </div>
              )}
            </div>

            <Pagination
              currentPage={page}
              totalPages={totalPages}
              onPageChange={setPage}
              className="rounded-t-none border-x-0 border-b-0 border-t border-white/[0.06] py-2.5 bg-white/[0.02]"
            />
          </>
        )}
      </div>

      {selectedRepo && (
        <RepositorySettingsDialog
          repoId={selectedRepo.id}
          repoName={selectedRepo.name}
          isOpen={settingsOpen}
          onClose={handleCloseSettings}
          initialSettings={repoSettings}
        />
      )}
    </AppShell>
  )
}
