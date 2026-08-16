"use client"

import { useEffect } from "react"
import { AppShell } from "@/components/layout/app-shell"
import { ErrorState } from "@/components/ui/error-state"

export default function LedgerError({
  error,
  reset,
}: {
  error: Error & { digest?: string }
  reset: () => void
}) {
  useEffect(() => {
    console.error("Ledger page error:", error)
  }, [error])

  return (
    <AppShell>
      <div className="py-8">
        <ErrorState
          title="Unable to load security ledger"
          message="Failed to retrieve historical compliance and trend metrics. Please try again."
          onRetry={() => reset()}
        />
      </div>
    </AppShell>
  )
}
