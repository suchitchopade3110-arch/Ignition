"use client"

import { useQuery } from "@tanstack/react-query"
import { apiClient } from "@/lib/api-client"
import { queryKeys } from "@/lib/query-keys"
import { Repository } from "@/types"

export function useRepositories() {
  return useQuery<Repository[]>({
    queryKey: queryKeys.repos.list(),
    queryFn: () => apiClient.getRepositories(),
    staleTime: 60 * 1000, // 1 minute
  })
}
