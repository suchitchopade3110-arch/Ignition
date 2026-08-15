"use client"

import { useState, useEffect, useRef } from "react"
import { useQueryClient } from "@tanstack/react-query"
import { AgentProgress, Finding, ReviewDetail, ReviewStatusType, SseEventPayload } from "@/types"
import { appConfig } from "@/lib/config"
import { queryKeys } from "@/lib/query-keys"

export type ConnectionState =
  | "idle"
  | "connecting"
  | "open"
  | "reconnecting"
  | "closed"
  | "failed"
  | "completed"

interface StreamState {
  status: ReviewStatusType
  agents: AgentProgress[]
  findings: Finding[]
  connectionState: ConnectionState
  error: Error | null
  reconnectAttempt: number
  liveAnnouncement: string | null
}

interface InitialData {
  status?: ReviewStatusType
  agents?: AgentProgress[]
  findings?: Finding[]
}

const MAX_RECONNECT_ATTEMPTS = 5
const INITIAL_BACKOFF_MS = 1000
const MAX_BACKOFF_MS = 10000

export function formatAgentName(agentId?: string): string {
  if (!agentId) return "Analysis agent"
  const clean = agentId.replace(/^agent_\d+[a-z]?_/, "").replace(/_/g, " ")
  return clean.charAt(0).toUpperCase() + clean.slice(1)
}

export function useReviewStream(reviewId: string, initialData?: InitialData) {
  const queryClient = useQueryClient()

  const [state, setState] = useState<StreamState>({
    status: initialData?.status || "queued",
    agents: initialData?.agents || [],
    findings: initialData?.findings || [],
    connectionState: "idle",
    error: null,
    reconnectAttempt: 0,
    liveAnnouncement: null,
  })

  const eventSourceRef = useRef<EventSource | null>(null)
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null)
  const reconnectAttemptsRef = useRef(0)
  const isMountedRef = useRef(true)

  // Keep queryClient ref updated for event callbacks
  const queryClientRef = useRef(queryClient)
  queryClientRef.current = queryClient

  useEffect(() => {
    isMountedRef.current = true

    // Only initiate connection if the review is in a running or queued state
    const isTerminal =
      state.status === "completed" ||
      state.status === "failed" ||
      state.status === "waiting_hitl" ||
      state.status === "cancelled"

    if (isTerminal) {
      setState((s) => ({
        ...s,
        connectionState: s.status === "completed" ? "completed" : "closed",
      }))
      return
    }

    const cleanupConnection = () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close()
        eventSourceRef.current = null
      }
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current)
        reconnectTimeoutRef.current = null
      }
    }

    const connect = () => {
      cleanupConnection()

      if (!isMountedRef.current) return

      // In mock development mode without a live backend, avoid connecting dead SSE
      if (appConfig.isMockEnabled() && !appConfig.apiUrl) {
        setState((s) => ({
          ...s,
          connectionState: "closed",
          error: null,
        }))
        return
      }

      setState((s) => ({
        ...s,
        connectionState: reconnectAttemptsRef.current > 0 ? "reconnecting" : "connecting",
        error: null,
      }))

      const url = `${appConfig.apiUrl}/reviews/${encodeURIComponent(reviewId)}/stream`

      try {
        const es = new EventSource(url, { withCredentials: true })
        eventSourceRef.current = es

        es.onopen = () => {
          if (!isMountedRef.current) return
          reconnectAttemptsRef.current = 0
          setState((s) => ({
            ...s,
            connectionState: "open",
            reconnectAttempt: 0,
            error: null,
          }))
        }

        es.onerror = () => {
          if (!isMountedRef.current) return

          es.close()
          eventSourceRef.current = null

          if (reconnectAttemptsRef.current < MAX_RECONNECT_ATTEMPTS) {
            reconnectAttemptsRef.current++
            const currentAttempt = reconnectAttemptsRef.current
            const backoff = Math.min(
              INITIAL_BACKOFF_MS * Math.pow(2, currentAttempt - 1),
              MAX_BACKOFF_MS
            )

            setState((s) => ({
              ...s,
              connectionState: "reconnecting",
              reconnectAttempt: currentAttempt,
              error: new Error(
                `Connection lost. Reconnecting in ${Math.round(backoff / 1000)}s (Attempt ${currentAttempt}/${MAX_RECONNECT_ATTEMPTS})...`
              ),
            }))

            reconnectTimeoutRef.current = setTimeout(connect, backoff)
          } else {
            setState((s) => ({
              ...s,
              connectionState: "failed",
              reconnectAttempt: reconnectAttemptsRef.current,
              error: new Error(
                "Real-time streaming disconnected after multiple retry attempts. Please refresh to load latest results."
              ),
            }))
          }
        }

        // --- Event Listeners with Query Cache Synchronization & Accessible Announcements ---

        es.addEventListener("review.started", () => {
          if (!isMountedRef.current) return
          setState((s) => ({ ...s, status: "running" }))

          queryClientRef.current.setQueryData<ReviewDetail>(
            queryKeys.reviews.detail(reviewId),
            (old) => (old ? { ...old, status: "running" } : old)
          )
        })

        es.addEventListener("agent.started", (e) => {
          if (!isMountedRef.current) return
          try {
            const payload: SseEventPayload = JSON.parse(e.data)
            setState((s) => {
              const agents = [...s.agents]
              const idx = agents.findIndex((a) => a.id === payload.agentId)
              if (idx !== -1) {
                agents[idx] = { ...agents[idx], status: "running" }
              }
              return { ...s, agents }
            })

            queryClientRef.current.setQueryData<ReviewDetail>(
              queryKeys.reviews.detail(reviewId),
              (old) => {
                if (!old) return old
                const updatedAgents = [...old.agents]
                const idx = updatedAgents.findIndex((a) => a.id === payload.agentId)
                if (idx !== -1) {
                  updatedAgents[idx] = { ...updatedAgents[idx], status: "running" }
                }
                return { ...old, agents: updatedAgents, status: "running" }
              }
            )
          } catch {
            // Malformed event payload safely ignored
          }
        })

        es.addEventListener("agent.completed", (e) => {
          if (!isMountedRef.current) return
          try {
            const payload: SseEventPayload = JSON.parse(e.data)
            const agentName = formatAgentName(payload.agentId)
            const announcement = `${agentName} analysis completed.`

            setState((s) => {
              const agents = [...s.agents]
              const idx = agents.findIndex((a) => a.id === payload.agentId)
              if (idx !== -1) {
                agents[idx] = {
                  ...agents[idx],
                  status: "completed",
                  executionTimeMs: payload.executionTimeMs,
                  findingCount: payload.findingCount ?? agents[idx].findingCount,
                }
              }
              return { ...s, agents, liveAnnouncement: announcement }
            })

            queryClientRef.current.setQueryData<ReviewDetail>(
              queryKeys.reviews.detail(reviewId),
              (old) => {
                if (!old) return old
                const updatedAgents = [...old.agents]
                const idx = updatedAgents.findIndex((a) => a.id === payload.agentId)
                if (idx !== -1) {
                  updatedAgents[idx] = {
                    ...updatedAgents[idx],
                    status: "completed",
                    executionTimeMs: payload.executionTimeMs,
                    findingCount: payload.findingCount ?? updatedAgents[idx].findingCount,
                  }
                }
                return { ...old, agents: updatedAgents }
              }
            )
          } catch {
            // Malformed event payload safely ignored
          }
        })

        es.addEventListener("agent.failed", (e) => {
          if (!isMountedRef.current) return
          try {
            const payload: SseEventPayload = JSON.parse(e.data)
            const agentName = formatAgentName(payload.agentId)
            const announcement = `${agentName} analysis failed.`

            setState((s) => {
              const agents = [...s.agents]
              const idx = agents.findIndex((a) => a.id === payload.agentId)
              if (idx !== -1) {
                agents[idx] = { ...agents[idx], status: "failed" }
              }
              return { ...s, agents, liveAnnouncement: announcement }
            })

            queryClientRef.current.setQueryData<ReviewDetail>(
              queryKeys.reviews.detail(reviewId),
              (old) => {
                if (!old) return old
                const updatedAgents = [...old.agents]
                const idx = updatedAgents.findIndex((a) => a.id === payload.agentId)
                if (idx !== -1) {
                  updatedAgents[idx] = { ...updatedAgents[idx], status: "failed" }
                }
                return { ...old, agents: updatedAgents }
              }
            )
          } catch {
            // Malformed event payload safely ignored
          }
        })

        es.addEventListener("acs.updated", (e) => {
          if (!isMountedRef.current) return
          try {
            const payload: SseEventPayload = JSON.parse(e.data)
            if (payload.acsScore !== undefined) {
              const announcement = `Architecture Compliance Score updated to ${payload.acsScore}.`
              setState((s) => ({ ...s, liveAnnouncement: announcement }))

              queryClientRef.current.setQueryData<ReviewDetail>(
                queryKeys.reviews.detail(reviewId),
                (old) => (old ? { ...old, acsScore: payload.acsScore } : old)
              )
            }
          } catch {
            // Malformed event payload safely ignored
          }
        })

        es.addEventListener("review.completed", () => {
          if (!isMountedRef.current) return
          cleanupConnection()
          setState((s) => ({
            ...s,
            status: "completed",
            connectionState: "completed",
            liveAnnouncement: "Autonomous code review completed.",
          }))

          // Invalidate and refetch authoritative review detail, list, stats & HITL
          queryClientRef.current.invalidateQueries({ queryKey: queryKeys.reviews.detail(reviewId) })
          queryClientRef.current.invalidateQueries({ queryKey: queryKeys.reviews.all() })
          queryClientRef.current.invalidateQueries({ queryKey: queryKeys.dashboard.stats() })
          queryClientRef.current.invalidateQueries({ queryKey: queryKeys.hitl.pending() })
        })

        es.addEventListener("review.failed", () => {
          if (!isMountedRef.current) return
          cleanupConnection()
          setState((s) => ({
            ...s,
            status: "failed",
            connectionState: "failed",
            error: new Error("Review processing encountered a fatal error."),
            liveAnnouncement: "Review analysis encountered an error.",
          }))

          queryClientRef.current.invalidateQueries({ queryKey: queryKeys.reviews.detail(reviewId) })
          queryClientRef.current.invalidateQueries({ queryKey: queryKeys.reviews.all() })
          queryClientRef.current.invalidateQueries({ queryKey: queryKeys.dashboard.stats() })
        })

        es.addEventListener("waiting.hitl", () => {
          if (!isMountedRef.current) return
          cleanupConnection()
          setState((s) => ({
            ...s,
            status: "waiting_hitl",
            connectionState: "closed",
            liveAnnouncement: "Review paused. Manual human approval required.",
          }))

          queryClientRef.current.invalidateQueries({ queryKey: queryKeys.reviews.detail(reviewId) })
          queryClientRef.current.invalidateQueries({ queryKey: queryKeys.reviews.all() })
          queryClientRef.current.invalidateQueries({ queryKey: queryKeys.hitl.pending() })
          queryClientRef.current.invalidateQueries({ queryKey: queryKeys.dashboard.stats() })
        })
      } catch (err) {
        setState((s) => ({
          ...s,
          connectionState: "failed",
          error: err instanceof Error ? err : new Error("Failed to initialize SSE connection"),
        }))
      }
    }

    connect()

    return () => {
      isMountedRef.current = false
      cleanupConnection()
    }
  }, [reviewId, state.status])

  return state
}
