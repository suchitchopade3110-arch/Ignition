/**
 * Centralized Application Configuration
 * Authoritative source for API base URLs, auth endpoints, and runtime flags.
 */

const isProduction = process.env.NODE_ENV === "production"
const explicitDemoMode = process.env.NEXT_PUBLIC_DEMO_MODE === "true"

// Fallback is only permitted during non-production development when demo mode is active
const rawApiUrl = process.env.NEXT_PUBLIC_API_URL?.trim()
const rawBackendUrl = process.env.NEXT_PUBLIC_BACKEND_URL?.trim()

function resolveApiUrl(): string {
  if (rawApiUrl) {
    return rawApiUrl.replace(/\/+$/, "")
  }
  if (!isProduction) {
    return "http://localhost:8000/api"
  }
  // In production, missing API URL is a fatal misconfiguration
  return ""
}

function resolveBackendUrl(): string {
  if (rawBackendUrl) {
    return rawBackendUrl.replace(/\/+$/, "")
  }
  if (rawApiUrl) {
    // Strip trailing /api if present to get backend root (used for OAuth redirects)
    return rawApiUrl.replace(/\/+$/, "").replace(/\/api$/, "")
  }
  if (!isProduction) {
    return "http://localhost:8000"
  }
  return ""
}

export const appConfig = {
  isProduction,
  isDemoMode: explicitDemoMode,
  apiUrl: resolveApiUrl(),
  backendUrl: resolveBackendUrl(),

  /**
   * Helper to check if mock data is permitted.
   * Mock data is NEVER permitted in production unless explicit demo mode is set.
   */
  isMockEnabled(): boolean {
    return explicitDemoMode || (!isProduction && !rawApiUrl)
  },

  /**
   * Validates runtime configuration for API calls.
   * Throws a descriptive error if running in production without required API URL.
   */
  validateApiConfig(): void {
    if (isProduction && !this.apiUrl && !this.isDemoMode) {
      throw new Error(
        "Application misconfiguration: NEXT_PUBLIC_API_URL must be specified in production."
      )
    }
  },
} as const
