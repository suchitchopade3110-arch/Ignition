"use client"

import { useQuery } from "@tanstack/react-query"
import { apiClient } from "@/lib/api-client"
import { queryKeys } from "@/lib/query-keys"
import { Review } from "@/types"

export interface ReviewFilters {
  repo?: string
  status?: string
  severity?: string
}

export function useReviews(filters?: ReviewFilters) {
  return useQuery<Review[]>({
    queryKey: queryKeys.reviews.list(filters),
    queryFn: () => apiClient.getReviews(filters?.repo, filters?.status, filters?.severity),
    staleTime: 30 * 1000,
  })
}
