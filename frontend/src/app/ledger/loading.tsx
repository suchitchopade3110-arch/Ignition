import { AppShell } from "@/components/layout/app-shell"
import { PageHeader } from "@/components/layout/page-header"

export default function LedgerLoading() {
  return (
    <AppShell>
      <div className="flex flex-col sm:flex-row sm:items-center justify-between mb-8 gap-4 border-b border-border pb-6">
        <PageHeader
          title="Security Ledger"
          description="Historical AI review metrics and Architecture Compliance Score (ACS) trends."
        />
      </div>

      <div className="space-y-8">
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="bg-card border border-border rounded-xl p-6 h-24 animate-pulse" />
          ))}
        </div>
        <div className="bg-card border border-border rounded-xl p-6 h-[380px] mb-8 animate-pulse" />
      </div>
    </AppShell>
  )
}
