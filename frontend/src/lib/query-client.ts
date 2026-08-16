import { QueryClient, isServer } from "@tanstack/react-query"
import { ApiError } from "./errors"

/**
 * Custom retry policy:
 * - 401, 403, 404, 422: Zero retries (immediately fail)
 * - Server errors (5xx) or Network errors: Up to 2 retries
 */
export function queryRetryPolicy(failureCount: number, error: unknown): boolean {
  if (error instanceof ApiError) {
    if (error.isAuthError || error.isForbidden || error.isNotFound || error.isValidationError) {
      return false
    }
    if (error.isServerError || error.isNetworkError) {
      return failureCount < 2
    }
  }

  // Generic Error check
  if (error instanceof Error && "status" in error) {
    const status = (error as { status: number }).status
    if (status === 401 || status === 403 || status === 404 || status === 422) {
      return false
    }
  }

  return failureCount < 2
}

export function makeQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 60 * 1000, // 1 minute
        gcTime: 5 * 60 * 1000, // 5 minutes
        retry: queryRetryPolicy,
        refetchOnWindowFocus: false,
        refetchOnReconnect: true,
      },
      mutations: {
        retry: false, // Do not automatically retry mutations
      },
    },
  })
}

let browserQueryClient: QueryClient | undefined = undefined

export function getQueryClient(): QueryClient {
  if (isServer) {
    // Server: always make a new query client
    return makeQueryClient()
  } else {
    // Browser: create once and reuse
    if (!browserQueryClient) {
      browserQueryClient = makeQueryClient()
    }
    return browserQueryClient
  }
}
