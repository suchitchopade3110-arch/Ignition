"use client"

import { useEffect } from "react"
import Link from "next/link"
import { AppShell } from "@/components/layout/app-shell"
import { ErrorState } from "@/components/ui/error-state"
import { ArrowLeft } from "lucide-react"

export default function ReviewDetailError({
  error,
  reset,
}: {
  error: Error & { digest?: string }
  reset: () => void
}) {
  useEffect(() => {
    console.error("Review detail error:", error)
  }, [error])

  return (
    <AppShell>
      <div className="py-8 space-y-6">
        <Link
          href="/reviews"
          className="inline-flex items-center gap-2 text-xs font-semibold text-muted-foreground hover:text-foreground transition-colors min-h-[44px]"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to Code Reviews
        </Link>
        <ErrorState
          title="Unable to load review details"
          message="We could not fetch the analysis data and findings for this review. The review may have been deleted or the server may be temporarily unreachable."
          onRetry={() => reset()}
        />
      </div>
    </AppShell>
  )
}
