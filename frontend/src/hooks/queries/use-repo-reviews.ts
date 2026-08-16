"use client"

import { useQuery } from "@tanstack/react-query"
import { apiClient } from "@/lib/api-client"
import { queryKeys } from "@/lib/query-keys"
import { Paginated, Review } from "@/types"

export function useRepoReviews(repoFullName: string | null | undefined, page: number = 1, pageSize: number = 25) {
  return useQuery<Paginated<Review>>({
    queryKey: queryKeys.repos.reviews(repoFullName || "", page, pageSize),
    queryFn: () => {
      if (!repoFullName) throw new Error("Repository full name required")
      return apiClient.getRepoReviews(repoFullName, page, pageSize)
    },
    enabled: Boolean(repoFullName),
    staleTime: 30 * 1000,
  })
}
