import { AppShell } from "@/components/layout/app-shell"
import { PageHeader } from "@/components/layout/page-header"
import { TableSkeleton, Skeleton } from "@/components/ui/loading-skeleton"

export default function ReviewsLoading() {
  return (
    <AppShell>
      <PageHeader
        title="Code Reviews"
        description="Monitor ongoing and completed autonomous AI code reviews across all repositories."
      />

      <div className="mb-6 flex items-center justify-between gap-4">
        <Skeleton className="h-10 w-full max-w-md rounded-lg" />
      </div>

      <div className="bg-card rounded-xl border border-border p-6">
        <TableSkeleton rows={8} />
      </div>
    </AppShell>
  )
}
