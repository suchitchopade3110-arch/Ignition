"use client"

import { useMutation, useQueryClient } from "@tanstack/react-query"
import { apiClient } from "@/lib/api-client"
import { queryKeys } from "@/lib/query-keys"
import { RepositorySettings } from "@/types"

interface UpdateRepoSettingsParams {
  repoId: string
  settings: RepositorySettings
}

export function useUpdateRepoSettingsMutation() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ repoId, settings }: UpdateRepoSettingsParams) =>
      apiClient.updateRepoSettings(repoId, settings),
    onSuccess: (updatedSettings, { repoId }) => {
      // Direct cache update for the specific repo settings
      queryClient.setQueryData(queryKeys.repos.settings(repoId), updatedSettings)
      // Invalidate repo lists to reflect potential status changes
      queryClient.invalidateQueries({ queryKey: queryKeys.repos.list() })
    },
  })
}
