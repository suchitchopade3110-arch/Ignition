/**
 * Structured API and Network Error abstractions.
 */

export class ApiError extends Error {
  readonly status: number
  readonly statusText: string
  readonly detail?: string
  readonly isNetworkError: boolean
  readonly code?: string

  constructor(params: {
    message: string
    status?: number
    statusText?: string
    detail?: string
    isNetworkError?: boolean
    code?: string
  }) {
    super(params.message)
    this.name = "ApiError"
    this.status = params.status ?? 0
    this.statusText = params.statusText ?? ""
    this.detail = params.detail
    this.isNetworkError = params.isNetworkError ?? false
    this.code = params.code

    // Maintain prototype chain
    Object.setPrototypeOf(this, ApiError.prototype)
  }

  get isAuthError(): boolean {
    return this.status === 401
  }

  get isForbidden(): boolean {
    return this.status === 403
  }

  get isNotFound(): boolean {
    return this.status === 404
  }

  get isValidationError(): boolean {
    return this.status === 422
  }

  get isRateLimited(): boolean {
    return this.status === 429
  }

  get isServerError(): boolean {
    return this.status >= 500 && this.status < 600
  }

  /**
   * Sanitized user-facing message safe to present in UI without technical internals.
   */
  getUserMessage(): string {
    if (this.isNetworkError) {
      return "Unable to connect to the server. Please check your internet connection."
    }
    if (this.isAuthError) {
      return "Your session has expired. Please sign in again."
    }
    if (this.isForbidden) {
      return "You do not have permission to access this resource."
    }
    if (this.isNotFound) {
      return "The requested resource was not found."
    }
    if (this.isRateLimited) {
      return "Rate limit exceeded. Please wait a moment before trying again."
    }
    if (this.isServerError) {
      return "The server encountered an error. Please try again later."
    }
    if (this.detail && typeof this.detail === "string" && this.detail.length < 150) {
      return this.detail
    }
    return this.message || "An unexpected error occurred."
  }
}
