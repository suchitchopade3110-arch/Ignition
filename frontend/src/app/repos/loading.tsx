import { AppShell } from "@/components/layout/app-shell"
import { PageHeader } from "@/components/layout/page-header"
import { TableSkeleton } from "@/components/ui/loading-skeleton"

export default function ReposLoading() {
  return (
    <AppShell>
      <PageHeader
        title="Repositories"
        description="Manage connected repositories and view Architecture Compliance Scores."
      />
      <div className="mb-4 h-10 w-64 rounded-lg bg-secondary/30 animate-pulse" />
      <div className="bg-card/25 border border-border rounded-xl p-6 shadow-sm">
        <TableSkeleton rows={6} />
      </div>
    </AppShell>
  )
}
