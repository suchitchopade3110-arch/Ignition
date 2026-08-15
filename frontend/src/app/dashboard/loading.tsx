import { AppShell } from "@/components/layout/app-shell"
import { PageHeader } from "@/components/layout/page-header"
import { CardSkeleton, TableSkeleton } from "@/components/ui/loading-skeleton"

export default function DashboardLoading() {
  return (
    <AppShell>
      <PageHeader
        title="Command Center"
        description="Monitor live AI reviews, pending approvals, and architecture health."
      />
      <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4 mb-8">
        <CardSkeleton />
        <CardSkeleton />
        <CardSkeleton />
        <CardSkeleton />
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="border border-border bg-card/20 rounded-xl p-6">
          <TableSkeleton rows={4} />
        </div>
        <div className="border border-border bg-card/20 rounded-xl p-6">
          <TableSkeleton rows={4} />
        </div>
      </div>
    </AppShell>
  )
}
