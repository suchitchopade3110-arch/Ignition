"use client"

import { useEffect } from "react"
import { AppShell } from "@/components/layout/app-shell"
import { ErrorState } from "@/components/ui/error-state"

export default function ReviewsError({
  error,
  reset,
}: {
  error: Error & { digest?: string }
  reset: () => void
}) {
  useEffect(() => {
    console.error("Reviews list error:", error)
  }, [error])

  return (
    <AppShell>
      <div className="py-8">
        <ErrorState
          title="Unable to load code reviews"
          message="An error occurred while fetching the review pipeline history. Please try again."
          onRetry={() => reset()}
        />
      </div>
    </AppShell>
  )
}
