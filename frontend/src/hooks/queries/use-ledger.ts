"use client"

import { useQuery } from "@tanstack/react-query"
import { apiClient } from "@/lib/api-client"
import { queryKeys } from "@/lib/query-keys"
import { LedgerStats, LedgerTrend } from "@/types"

export function useLedgerStats(repoFullName: string | null | undefined) {
  return useQuery<LedgerStats>({
    queryKey: queryKeys.ledger.stats(repoFullName || ""),
    queryFn: () => {
      if (!repoFullName) throw new Error("Repository full name required")
      return apiClient.getLedgerStats(repoFullName)
    },
    enabled: Boolean(repoFullName),
    staleTime: 60 * 1000,
  })
}

export function useLedgerTrend(repoFullName: string | null | undefined) {
  return useQuery<LedgerTrend[]>({
    queryKey: queryKeys.ledger.trend(repoFullName || ""),
    queryFn: () => {
      if (!repoFullName) throw new Error("Repository full name required")
      return apiClient.getLedgerTrend(repoFullName)
    },
    enabled: Boolean(repoFullName),
    staleTime: 60 * 1000,
  })
}
