"use client"

import { useQuery } from "@tanstack/react-query"
import { apiClient } from "@/lib/api-client"
import { queryKeys } from "@/lib/query-keys"
import { HitlItem } from "@/types"

export function useHitlPending() {
  return useQuery<HitlItem[]>({
    queryKey: queryKeys.hitl.pending(),
    queryFn: () => apiClient.getHitlPending(),
    staleTime: 15 * 1000,
  })
}
