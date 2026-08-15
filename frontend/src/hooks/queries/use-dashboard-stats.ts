"use client"

import { useQuery } from "@tanstack/react-query"
import { apiClient } from "@/lib/api-client"
import { queryKeys } from "@/lib/query-keys"
import { DashboardStats } from "@/types"

export function useDashboardStats() {
  return useQuery<DashboardStats>({
    queryKey: queryKeys.dashboard.stats(),
    queryFn: () => apiClient.getDashboardStats(),
    staleTime: 30 * 1000, // 30 seconds
  })
}
