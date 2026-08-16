"use client"

import { useMutation, useQueryClient } from "@tanstack/react-query"
import { apiClient } from "@/lib/api-client"
import { queryKeys } from "@/lib/query-keys"

export function useApproveHitlMutation() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (reviewId: string) => apiClient.approveHitl(reviewId),
    onSuccess: (_, reviewId) => {
      // Invalidate HITL pending queue
      queryClient.invalidateQueries({ queryKey: queryKeys.hitl.pending() })
      // Invalidate the affected review detail
      queryClient.invalidateQueries({ queryKey: queryKeys.reviews.detail(reviewId) })
      // Invalidate review list and stats
      queryClient.invalidateQueries({ queryKey: queryKeys.reviews.all() })
      queryClient.invalidateQueries({ queryKey: queryKeys.dashboard.stats() })
    },
  })
}

export function useRejectHitlMutation() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (reviewId: string) => apiClient.rejectHitl(reviewId),
    onSuccess: (_, reviewId) => {
      // Invalidate HITL pending queue
      queryClient.invalidateQueries({ queryKey: queryKeys.hitl.pending() })
      // Invalidate the affected review detail
      queryClient.invalidateQueries({ queryKey: queryKeys.reviews.detail(reviewId) })
      // Invalidate review list and stats
      queryClient.invalidateQueries({ queryKey: queryKeys.reviews.all() })
      queryClient.invalidateQueries({ queryKey: queryKeys.dashboard.stats() })
    },
  })
}
