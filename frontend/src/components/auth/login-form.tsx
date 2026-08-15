"use client"

import { useSearchParams } from "next/navigation"
import { AlertCircle } from "lucide-react"
import { appConfig } from "@/lib/config"

export function LoginForm() {
  const searchParams = useSearchParams()
  const isExpired = searchParams.get("expired") === "true"
  const errorMsg = searchParams.get("error")

  const loginUrl = `${appConfig.backendUrl}/auth/github/login`

  return (
    <div className="space-y-6">
      {/* Session Expired / Auth Error Notification */}
      {isExpired && (
        <div className="flex items-center gap-2.5 p-3 rounded-lg bg-warning/10 border border-warning/30 text-warning text-xs font-medium animate-in fade-in-50">
          <AlertCircle className="h-4 w-4 shrink-0" />
          <span>Your session has expired. Please sign in again.</span>
        </div>
      )}

      {errorMsg && (
        <div className="flex items-center gap-2.5 p-3 rounded-lg bg-critical/10 border border-critical/30 text-critical text-xs font-medium animate-in fade-in-50">
          <AlertCircle className="h-4 w-4 shrink-0" />
          <span>{errorMsg}</span>
        </div>
      )}

      <div>
        <a
          href={loginUrl}
          className="w-full min-h-[44px] flex justify-center items-center gap-2.5 py-2.5 px-4 border border-border rounded-lg shadow-sm bg-background text-sm font-medium text-foreground hover:bg-secondary transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-primary focus-visible:ring-offset-background"
        >
          <svg className="h-5 w-5" fill="currentColor" viewBox="0 0 24 24" aria-hidden="true">
            <path
              fillRule="evenodd"
              d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.531 1.032 1.531 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z"
              clipRule="evenodd"
            />
          </svg>
          Continue with GitHub
        </a>
      </div>

      <div className="relative">
        <div className="absolute inset-0 flex items-center">
          <div className="w-full border-t border-border" />
        </div>
        <div className="relative flex justify-center text-sm">
          <span className="px-2 bg-card text-muted-foreground">Enterprise SSO</span>
        </div>
      </div>

      <div>
        <button
          type="button"
          disabled
          aria-disabled="true"
          className="w-full min-h-[44px] flex justify-center items-center py-2.5 px-4 border border-transparent rounded-lg shadow-sm text-sm font-medium text-primary-foreground bg-primary/80 cursor-not-allowed opacity-50 transition-colors"
        >
          Sign in with SAML
        </button>
      </div>
    </div>
  )
}
