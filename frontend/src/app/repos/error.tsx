"use client"

import { useEffect } from "react"
import { AppShell } from "@/components/layout/app-shell"
import { ErrorState } from "@/components/ui/error-state"

export default function ReposError({
  error,
  reset,
}: {
  error: Error & { digest?: string }
  reset: () => void
}) {
  useEffect(() => {
    console.error("Repositories page error:", error)
  }, [error])

  return (
    <AppShell>
      <div className="py-8">
        <ErrorState
          title="Unable to load repositories"
          message="Failed to fetch connected repositories from the server. Please verify your connection and try again."
          onRetry={() => reset()}
        />
      </div>
    </AppShell>
  )
}
