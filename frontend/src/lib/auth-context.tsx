"use client"

import React, { createContext, useContext, useEffect, useState, useCallback, useTransition } from "react"
import { useRouter, usePathname } from "next/navigation"
import { AuthUser } from "@/types"
import { apiClient } from "./api-client"
import { ApiError } from "./errors"

export type AuthStatus = "loading" | "authenticated" | "unauthenticated" | "error"

interface AuthContextValue {
  status: AuthStatus
  user: AuthUser | null
  error: string | null
  refreshAuth: () => Promise<void>
  logout: () => Promise<void>
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined)

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const router = useRouter()
  const pathname = usePathname()
  const [, startTransition] = useTransition()
  const [status, setStatus] = useState<AuthStatus>("loading")
  const [user, setUser] = useState<AuthUser | null>(null)
  const [error, setError] = useState<string | null>(null)

  const refreshAuth = useCallback(async () => {
    try {
      setError(null)
      const currentUser = await apiClient.getAuthMe()
      setUser(currentUser)
      setStatus("authenticated")
    } catch (err: unknown) {
      setUser(null)
      if (err instanceof ApiError && err.isAuthError) {
        setStatus("unauthenticated")
      } else if (err instanceof ApiError && err.isNetworkError) {
        setStatus("error")
        setError(err.getUserMessage())
      } else {
        setStatus("unauthenticated")
      }
    }
  }, [])

  const logout = useCallback(async () => {
    try {
      await apiClient.logout()
    } catch (err) {
      console.warn("Logout request failed on server, completing local logout:", err)
    } finally {
      setUser(null)
      setStatus("unauthenticated")
      startTransition(() => {
        router.push("/login")
      })
    }
  }, [router])

  // Bootstrap session check on mount
  useEffect(() => {
    refreshAuth()
  }, [refreshAuth])

  // Handle global 401 Unauthorized events from any API call
  useEffect(() => {
    const unsubscribe = apiClient.onUnauthorized(() => {
      setUser(null)
      setStatus("unauthenticated")
      const publicPaths = ["/", "/login"]
      if (!publicPaths.includes(pathname || "")) {
        startTransition(() => {
          router.push("/login?expired=true")
        })
      }
    })
    return unsubscribe
  }, [pathname, router])

  return (
    <AuthContext.Provider value={{ status, user, error, refreshAuth, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider")
  }
  return context
}
