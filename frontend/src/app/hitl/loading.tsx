import { AppShell } from "@/components/layout/app-shell"
import { PageHeader } from "@/components/layout/page-header"
import { TableSkeleton } from "@/components/ui/loading-skeleton"

export default function HitlLoading() {
  return (
    <AppShell>
      <PageHeader
        title="Human-in-the-Loop (HITL)"
        description="Manual approval queue for reviews flagged with critical security or architectural regressions."
      />

      <div className="bg-card border border-border rounded-xl p-6 mt-6">
        <TableSkeleton rows={4} />
      </div>
    </AppShell>
  )
}
