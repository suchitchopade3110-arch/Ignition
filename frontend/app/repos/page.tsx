"use client"

import { useEffect, useState } from "react"
import { AppShell } from "@/components/app-shell"
import { PageHeader } from "@/components/page-header"
import { SearchInput } from "@/components/search-input"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/table"
import { Pagination } from "@/components/pagination"
import { AcsScoreRing } from "@/components/acs-score-ring"
import { apiClient } from "@/lib/api-client"
import { Repository, RepositorySettings } from "@/lib/types"
import { TableSkeleton } from "@/components/loading-skeleton"
import { Settings, ExternalLink } from "lucide-react"
import { RepositorySettingsDialog } from "@/components/repository-settings-dialog"

export default function RepositoriesPage() {
  const [repos, setRepos] = useState<Repository[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState("")
  const [page, setPage] = useState(1)

  // Settings dialog state
  const [selectedRepo, setSelectedRepo] = useState<Repository | null>(null)
  const [settingsOpen, setSettingsOpen] = useState(false)
  const [repoSettings, setRepoSettings] = useState<RepositorySettings | undefined>(undefined)

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

  const handleOpenSettings = async (repo: Repository) => {
    setSelectedRepo(repo)
    setSettingsOpen(true)
    try {
      const settings = await apiClient.getRepoSettings(repo.id)
      setRepoSettings(settings)
    } catch {
      setRepoSettings(undefined)
    }
  }

  const handleCloseSettings = () => {
    setSettingsOpen(false)
    setSelectedRepo(null)
    setRepoSettings(undefined)
  }

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
          <button className="inline-flex items-center justify-center rounded-full text-xs font-semibold transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:opacity-50 disabled:pointer-events-none ring-offset-background bg-primary text-primary-foreground hover:bg-primary/90 h-9 py-2 px-4 shadow-[0_0_15px_rgba(255,69,0,0.15)]">
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

      <div className="bg-card/25 border border-border rounded-xl overflow-hidden shadow-sm">
        {loading ? (
          <div className="p-4">
            <TableSkeleton rows={5} />
          </div>
        ) : (
          <>
            <Table>
              <TableHeader>
                <TableRow className="bg-card/50">
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
                    <TableRow key={repo.id} className="hover:bg-secondary/20 transition-colors">
                      <TableCell className="font-semibold text-foreground py-2.5 text-sm">
                        <div className="flex items-center gap-2">
                          <span>{repo.name}</span>
                        </div>
                      </TableCell>
                      <TableCell className="text-muted-foreground py-2.5 text-xs">{repo.owner}</TableCell>
                      <TableCell className="py-2.5">
                        <span className="inline-flex items-center rounded bg-secondary px-2 py-0.5 text-[10px] font-semibold text-secondary-foreground border border-border">
                          {repo.language.toLowerCase()}
                        </span>
                      </TableCell>
                      <TableCell className="text-right py-2.5">
                        <div className="flex items-center justify-end">
                          <AcsScoreRing score={repo.acsScore} size={30} strokeWidth={2.5} />
                        </div>
                      </TableCell>
                      <TableCell className="py-2.5">
                        <div className="flex items-center justify-end gap-1.5">
                          <button className="text-muted-foreground hover:text-foreground transition-colors p-1.5 rounded hover:bg-secondary/60">
                            <ExternalLink className="h-3.5 w-3.5" />
                            <span className="sr-only">Open</span>
                          </button>
                          <button 
                            onClick={() => handleOpenSettings(repo)}
                            className="text-muted-foreground hover:text-foreground transition-colors p-1.5 rounded hover:bg-secondary/60"
                          >
                            <Settings className="h-3.5 w-3.5" />
                            <span className="sr-only">Settings</span>
                          </button>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))
                ) : (
                  <TableRow>
                    <TableCell colSpan={5} className="h-32 text-center text-muted-foreground text-sm">
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
              className="rounded-t-none border-x-0 border-b-0 py-2.5 bg-card/10"
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
