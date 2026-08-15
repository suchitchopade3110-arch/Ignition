"use client"

import { useEffect } from "react"
import { AppShell } from "@/components/layout/app-shell"
import { ErrorState } from "@/components/ui/error-state"

export default function DashboardError({
  error,
  reset,
}: {
  error: Error & { digest?: string }
  reset: () => void
}) {
  useEffect(() => {
    console.error("Dashboard error:", error)
  }, [error])

  return (
    <AppShell>
      <div className="py-8">
        <ErrorState
          title="Unable to load dashboard"
          message="We could not retrieve the latest review metrics or repository statuses from the server."
          onRetry={() => reset()}
        />
      </div>
    </AppShell>
  )
}
