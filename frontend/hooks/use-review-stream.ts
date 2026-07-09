"use client"

import { useState, useEffect, useRef } from "react"
import { AgentProgress, Finding, ReviewStatusType, SseEventPayload } from "@/lib/types"

interface StreamState {
  status: ReviewStatusType
  agents: AgentProgress[]
  findings: Finding[]
  connectionState: "connecting" | "open" | "closed" | "error"
  error: Error | null
}

export function useReviewStream(reviewId: string, initialData: any) {
  const [state, setState] = useState<StreamState>({
    status: initialData?.status || "queued",
    agents: initialData?.agents || [],
    findings: initialData?.findings || [],
    connectionState: "closed",
    error: null,
  })

  const eventSourceRef = useRef<EventSource | null>(null)
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null)

  useEffect(() => {
    // Only connect if the review is actively running or queued
    if (state.status !== "running" && state.status !== "queued") {
      setState(s => ({ ...s, connectionState: "closed" }))
      return
    }

    let reconnectAttempts = 0
    const maxReconnectAttempts = 5

    const connect = () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close()
      }

      setState(s => ({ ...s, connectionState: "connecting", error: null }))

      // Production SSE Endpoint
      const baseUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api"
      const url = `${baseUrl}/reviews/${reviewId}/stream`
      
      const es = new EventSource(url)
      eventSourceRef.current = es

      es.onopen = () => {
        setState(s => ({ ...s, connectionState: "open", error: null }))
        reconnectAttempts = 0
      }

      es.onerror = (err) => {
        es.close()
        eventSourceRef.current = null
        
        reconnectAttempts++
        if (reconnectAttempts <= maxReconnectAttempts) {
          setState(s => ({ 
            ...s, 
            connectionState: "error", 
            error: new Error(`Connection lost. Reconnecting (Attempt ${reconnectAttempts}/${maxReconnectAttempts})...`) 
          }))
          reconnectTimeoutRef.current = setTimeout(connect, Math.min(1000 * Math.pow(2, reconnectAttempts), 10000))
        } else {
          setState(s => ({ 
            ...s, 
            connectionState: "closed", 
            error: new Error("Failed to connect to real-time updates after multiple attempts.") 
          }))
        }
      }

      // Handle real SSE events
      es.addEventListener("review.started", (e) => {
        setState(s => ({ ...s, status: "running" }))
      })

      es.addEventListener("agent.started", (e) => {
        const payload: SseEventPayload = JSON.parse(e.data)
        setState(s => {
          const agents = [...s.agents]
          const idx = agents.findIndex(a => a.id === payload.agentId)
          if (idx !== -1) agents[idx] = { ...agents[idx], status: "running" }
          return { ...s, agents }
        })
      })

      es.addEventListener("agent.completed", (e) => {
        const payload: SseEventPayload = JSON.parse(e.data)
        setState(s => {
          const agents = [...s.agents]
          const idx = agents.findIndex(a => a.id === payload.agentId)
          if (idx !== -1) {
            agents[idx] = { 
              ...agents[idx], 
              status: "completed", 
              executionTimeMs: payload.executionTimeMs,
              findingCount: payload.findingCount || 0
            }
          }
          return { ...s, agents }
        })
      })

      es.addEventListener("agent.failed", (e) => {
        const payload: SseEventPayload = JSON.parse(e.data)
        setState(s => {
          const agents = [...s.agents]
          const idx = agents.findIndex(a => a.id === payload.agentId)
          if (idx !== -1) agents[idx] = { ...agents[idx], status: "failed" }
          return { ...s, agents }
        })
      })
      
      es.addEventListener("review.completed", () => {
        setState(s => ({ ...s, status: "completed", connectionState: "closed" }))
        es.close()
      })

      es.addEventListener("waiting.hitl", () => {
        setState(s => ({ ...s, status: "waiting_hitl", connectionState: "closed" }))
        es.close()
      })
    }

    connect()

    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close()
      }
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current)
      }
    }
  }, [reviewId]) // Deliberately omitted state.status from dep array to avoid thrashing connection

  return state
}
