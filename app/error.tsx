"use client"

import { useEffect } from "react"
import { AppShell } from "@/components/app-shell"
import { AlertTriangle, RefreshCw } from "lucide-react"

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string }
  reset: () => void
}) {
  useEffect(() => {
    // Log the error to an error reporting service in production
    console.error(error)
  }, [error])

  return (
    <AppShell>
      <div className="flex flex-col items-center justify-center min-h-[70vh] text-center px-4">
        <div className="bg-critical/10 border border-critical/20 p-6 rounded-full mb-6">
          <AlertTriangle className="h-12 w-12 text-critical" />
        </div>
        <h1 className="text-3xl font-bold tracking-tight text-foreground mb-3">Something went wrong</h1>
        <p className="text-muted-foreground max-w-md mb-8">
          An unexpected error occurred while processing your request. 
          Please try again or contact support if the issue persists.
        </p>
        <div className="bg-secondary/30 rounded-md p-4 mb-8 text-left w-full max-w-md border border-border/50">
          <p className="text-xs font-mono text-muted-foreground break-words">
            {error.message || "Internal Server Error"}
          </p>
        </div>
        <button 
          onClick={() => reset()}
          className="inline-flex items-center gap-2 justify-center rounded-md bg-primary px-6 py-2.5 text-sm font-medium text-primary-foreground hover:bg-primary/90 transition-colors"
        >
          <RefreshCw className="h-4 w-4" />
          Try Again
        </button>
      </div>
    </AppShell>
  )
}
