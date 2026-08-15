"use client"

import { useState, useRef, useEffect } from "react"
import { User, LogOut, Loader2 } from "lucide-react"
import { useAuth } from "@/lib/auth-context"

export function UserMenu() {
  const { user, status, logout } = useAuth()
  const [isOpen, setIsOpen] = useState(false)
  const [isLoggingOut, setIsLoggingOut] = useState(false)
  const menuRef = useRef<HTMLDivElement>(null)

  const handleLogout = async () => {
    setIsLoggingOut(true)
    try {
      await logout()
    } finally {
      setIsLoggingOut(false)
      setIsOpen(false)
    }
  }

  // Close dropdown on outside click or Escape key
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setIsOpen(false)
      }
    }

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setIsOpen(false)
      }
    }

    if (isOpen) {
      document.addEventListener("mousedown", handleClickOutside)
      document.addEventListener("keydown", handleKeyDown)
    }

    return () => {
      document.removeEventListener("mousedown", handleClickOutside)
      document.removeEventListener("keydown", handleKeyDown)
    }
  }, [isOpen])

  const initials = user?.name
    ? user.name
        .split(" ")
        .map((n: string) => n[0])
        .join("")
        .toUpperCase()
        .slice(0, 2)
    : user?.login
    ? user.login.slice(0, 2).toUpperCase()
    : "SE"

  return (
    <div className="relative flex items-center gap-3" ref={menuRef}>
      {/* User Avatar Button */}
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        aria-expanded={isOpen}
        aria-haspopup="menu"
        aria-label="User account menu"
        className="flex items-center justify-center min-h-[44px] min-w-[44px] rounded-full focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 focus-visible:ring-offset-background transition-all"
      >
        <div className="flex items-center justify-center h-8 w-8 rounded-full bg-secondary border border-border overflow-hidden hover:border-primary/50 transition-colors">
          {user?.avatar_url ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img src={user.avatar_url} alt={user.name || user.login} className="h-full w-full object-cover" />
          ) : user ? (
            <span className="text-xs font-semibold text-foreground font-mono">{initials}</span>
          ) : (
            <User className="h-4 w-4 text-muted-foreground" />
          )}
        </div>
      </button>

      {/* Accessible Dropdown Panel */}
      {isOpen && (
        <div
          role="menu"
          aria-orientation="vertical"
          className="absolute right-0 top-full mt-2 w-56 rounded-xl border border-white/[0.12] bg-elevated/90 backdrop-blur-lg p-1 shadow-lg shadow-black/30 z-50 animate-in fade-in-50 zoom-in-95 duration-100"
        >
          {user && (
            <div className="px-3 py-2.5 border-b border-white/[0.06]">
              <p className="text-xs font-semibold text-foreground truncate">{user.name || user.login}</p>
              <p className="text-[11px] font-mono text-muted-foreground truncate">@{user.login}</p>
            </div>
          )}

          <div className="py-1">
            <button
              type="button"
              role="menuitem"
              onClick={handleLogout}
              disabled={isLoggingOut || status === "loading"}
              className="w-full flex items-center gap-2.5 px-3 py-2.5 text-xs font-medium text-critical hover:bg-critical/10 rounded-lg transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary disabled:opacity-50 min-h-[44px]"
            >
              {isLoggingOut ? (
                <Loader2 className="h-4 w-4 animate-spin text-critical" />
              ) : (
                <LogOut className="h-4 w-4 text-critical" />
              )}
              <span>{isLoggingOut ? "Signing out..." : "Sign out"}</span>
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
