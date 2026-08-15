"use client"

import { AlertTriangle, RefreshCw } from "lucide-react"

interface ErrorStateProps {
  title?: string
  message?: string
  onRetry?: () => void
  isRetrying?: boolean
}

export function ErrorState({
  title = "Failed to load data",
  message = "An unexpected error occurred while communicating with the server. Please try again.",
  onRetry,
  isRetrying = false,
}: ErrorStateProps) {
  return (
    <div className="flex flex-col items-center justify-center rounded-xl border border-border/80 bg-card/60 px-6 py-12 text-center h-full min-h-[320px] shadow-sm">
      <div className="flex h-12 w-12 items-center justify-center rounded-full bg-critical/10 border border-critical/20 mb-4">
        <AlertTriangle className="h-6 w-6 text-critical" />
      </div>
      <h3 className="text-lg font-bold text-foreground mb-2">{title}</h3>
      <p className="text-sm text-muted-foreground max-w-md mx-auto mb-6 leading-relaxed">
        {message}
      </p>
      {onRetry && (
        <button
          type="button"
          onClick={onRetry}
          disabled={isRetrying}
          className="inline-flex items-center justify-center gap-2 min-h-[44px] px-5 py-2.5 rounded-lg bg-secondary border border-border text-xs font-semibold text-foreground hover:bg-secondary/80 hover:border-primary/50 transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 focus-visible:ring-offset-background disabled:opacity-50"
        >
          <RefreshCw className={`h-3.5 w-3.5 ${isRetrying ? "animate-spin text-primary" : ""}`} />
          <span>{isRetrying ? "Retrying..." : "Try Again"}</span>
        </button>
      )}
    </div>
  )
}
