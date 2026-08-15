"use client"

import { useQuery } from "@tanstack/react-query"
import { apiClient } from "@/lib/api-client"
import { queryKeys } from "@/lib/query-keys"
import { Review } from "@/types"

export function useRepoReviews(repoFullName: string | null | undefined) {
  return useQuery<Review[]>({
    queryKey: queryKeys.repos.reviews(repoFullName || ""),
    queryFn: () => {
      if (!repoFullName) throw new Error("Repository full name required")
      return apiClient.getRepoReviews(repoFullName)
    },
    enabled: Boolean(repoFullName),
    staleTime: 30 * 1000,
  })
}
