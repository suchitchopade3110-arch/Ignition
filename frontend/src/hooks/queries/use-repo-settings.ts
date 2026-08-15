"use client"

import { useQuery } from "@tanstack/react-query"
import { apiClient } from "@/lib/api-client"
import { queryKeys } from "@/lib/query-keys"
import { RepositorySettings } from "@/types"

export function useRepoSettings(repoId: string | null | undefined) {
  return useQuery<RepositorySettings>({
    queryKey: queryKeys.repos.settings(repoId || ""),
    queryFn: () => {
      if (!repoId) throw new Error("Repository ID required")
      return apiClient.getRepoSettings(repoId)
    },
    enabled: Boolean(repoId),
    staleTime: 60 * 1000,
  })
}
