import { describe, it, expect } from "vitest"
import { queryRetryPolicy } from "@/lib/query-client"
import { ApiError } from "@/lib/errors"

describe("queryRetryPolicy", () => {
  it("immediately denies retry on 401 Unauthorized", () => {
    const authError = new ApiError({
      message: "Unauthorized",
      status: 401,
      statusText: "Unauthorized",
    })
    expect(queryRetryPolicy(0, authError)).toBe(false)
    expect(queryRetryPolicy(1, authError)).toBe(false)
  })

  it("immediately denies retry on 403 Forbidden and 404 Not Found", () => {
    const forbiddenError = new ApiError({
      message: "Forbidden",
      status: 403,
      statusText: "Forbidden",
    })
    const notFoundError = new ApiError({
      message: "Not Found",
      status: 404,
      statusText: "Not Found",
    })
    expect(queryRetryPolicy(0, forbiddenError)).toBe(false)
    expect(queryRetryPolicy(0, notFoundError)).toBe(false)
  })

  it("immediately denies retry on 422 Validation Error", () => {
    const validationError = new ApiError({
      message: "Unprocessable Entity",
      status: 422,
      statusText: "Unprocessable Entity",
    })
    expect(queryRetryPolicy(0, validationError)).toBe(false)
  })

  it("permits up to 2 retries on 500 Server Error", () => {
    const serverError = new ApiError({
      message: "Internal Server Error",
      status: 500,
      statusText: "Internal Server Error",
    })
    expect(queryRetryPolicy(0, serverError)).toBe(true)
    expect(queryRetryPolicy(1, serverError)).toBe(true)
    expect(queryRetryPolicy(2, serverError)).toBe(false)
  })

  it("permits up to 2 retries on Network/Timeout errors", () => {
    const networkError = new ApiError({
      message: "Network request failed",
      isNetworkError: true,
    })
    expect(queryRetryPolicy(0, networkError)).toBe(true)
    expect(queryRetryPolicy(1, networkError)).toBe(true)
    expect(queryRetryPolicy(2, networkError)).toBe(false)
  })
})
