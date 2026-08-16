"use client"

import { useQuery } from "@tanstack/react-query"
import { apiClient } from "@/lib/api-client"
import { queryKeys } from "@/lib/query-keys"
import { ReviewDetail } from "@/types"

export function useReview(reviewId: string | null | undefined, initialData?: ReviewDetail) {
  return useQuery<ReviewDetail>({
    queryKey: queryKeys.reviews.detail(reviewId || ""),
    queryFn: () => {
      if (!reviewId) throw new Error("Review ID required")
      return apiClient.getReview(reviewId)
    },
    enabled: Boolean(reviewId),
    initialData,
    staleTime: 15 * 1000, // 15 seconds
  })
}
