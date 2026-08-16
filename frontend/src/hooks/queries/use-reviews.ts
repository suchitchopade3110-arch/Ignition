"use client"

import { useQuery } from "@tanstack/react-query"
import { apiClient } from "@/lib/api-client"
import { queryKeys } from "@/lib/query-keys"
import { Paginated, Review } from "@/types"

export interface ReviewFilters {
  repo?: string
  status?: string
  severity?: string
  page?: number
  pageSize?: number
}

export function useReviews(filters?: ReviewFilters) {
  const page = filters?.page ?? 1
  const pageSize = filters?.pageSize ?? 25

  return useQuery<Paginated<Review>>({
    queryKey: queryKeys.reviews.list({ ...filters, page, pageSize }),
    queryFn: () => apiClient.getReviews(filters?.repo, filters?.status, filters?.severity, page, pageSize),
    staleTime: 30 * 1000,
  })
}
