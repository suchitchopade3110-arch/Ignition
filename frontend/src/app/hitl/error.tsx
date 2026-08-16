"use client"

import { useEffect } from "react"
import { AppShell } from "@/components/layout/app-shell"
import { ErrorState } from "@/components/ui/error-state"

export default function HitlError({
  error,
  reset,
}: {
  error: Error & { digest?: string }
  reset: () => void
}) {
  useEffect(() => {
    console.error("HITL page error:", error)
  }, [error])

  return (
    <AppShell>
      <div className="py-8">
        <ErrorState
          title="Unable to load approval queue"
          message="Failed to fetch pending Human-in-the-Loop review requests. Please try again."
          onRetry={() => reset()}
        />
      </div>
    </AppShell>
  )
}
