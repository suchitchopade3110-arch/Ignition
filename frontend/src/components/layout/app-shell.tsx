"use client"

import { useState, useEffect, useRef } from "react"
import Link from "next/link"
import Image from "next/image"
import { usePathname } from "next/navigation"
import { Menu } from "lucide-react"
import { Sidebar } from "@/components/layout/sidebar"
import { UserMenu } from "@/components/layout/user-menu"
import { AuthGuard } from "@/components/auth/auth-guard"

export function AppShell({ children }: { children: React.ReactNode }) {
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false)
  const pathname = usePathname()
  const triggerRef = useRef<HTMLButtonElement | null>(null)
  const drawerRef = useRef<HTMLDivElement | null>(null)

  const prevPathnameRef = useRef(pathname)
  // Auto-close mobile drawer when route changes and return focus
  useEffect(() => {
    if (prevPathnameRef.current !== pathname) {
      prevPathnameRef.current = pathname
      if (isMobileMenuOpen) {
        setIsMobileMenuOpen(false)
        triggerRef.current?.focus()
      }
    }
  }, [pathname, isMobileMenuOpen])

  // Handle Escape key and focus trapping inside mobile drawer
  useEffect(() => {
    function handleKeyDown(event: KeyboardEvent) {
      if (!isMobileMenuOpen) return

      if (event.key === "Escape") {
        event.preventDefault()
        setIsMobileMenuOpen(false)
        triggerRef.current?.focus()
        return
      }

      if (event.key === "Tab" && drawerRef.current) {
        const focusableElements = drawerRef.current.querySelectorAll<HTMLElement>(
          'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
        )
        if (focusableElements.length === 0) return

        const firstElement = focusableElements[0]
        const lastElement = focusableElements[focusableElements.length - 1]

        if (event.shiftKey) {
          if (document.activeElement === firstElement) {
            event.preventDefault()
            lastElement.focus()
          }
        } else {
          if (document.activeElement === lastElement) {
            event.preventDefault()
            firstElement.focus()
          }
        }
      }
    }

    if (isMobileMenuOpen) {
      document.addEventListener("keydown", handleKeyDown)
      document.body.style.overflow = "hidden"

      // Focus first element in drawer on open
      setTimeout(() => {
        if (drawerRef.current) {
          const first = drawerRef.current.querySelector<HTMLElement>(
            'button, [href], [tabindex]:not([tabindex="-1"])'
          )
          first?.focus()
        }
      }, 50)
    } else {
      document.body.style.overflow = ""
    }

    return () => {
      document.removeEventListener("keydown", handleKeyDown)
      document.body.style.overflow = ""
    }
  }, [isMobileMenuOpen])

  const handleCloseDrawer = () => {
    setIsMobileMenuOpen(false)
    triggerRef.current?.focus()
  }

  return (
    <AuthGuard>
      <div className="flex h-screen overflow-hidden bg-background bg-ignition-pattern">
        {/* Desktop Fixed Sidebar */}
        <div className="hidden md:flex md:w-64 md:flex-col md:fixed md:inset-y-0 border-r border-white/[0.08] bg-card/65 backdrop-blur-md z-20">
          <Sidebar />
        </div>

        {/* Mobile Slide-out Drawer & Overlay Backdrop */}
        {isMobileMenuOpen && (
          <div
            className="fixed inset-0 z-50 md:hidden animate-in fade-in duration-200 motion-reduce:animate-none"
            role="dialog"
            aria-modal="true"
            aria-label="Navigation menu"
          >
            {/* Backdrop */}
            <div
              className="fixed inset-0 bg-black/80 backdrop-blur-xs transition-opacity"
              onClick={handleCloseDrawer}
              aria-hidden="true"
            />

            {/* Slide-out Panel with Focus Trap Ref */}
            <div
              ref={drawerRef}
              className="relative flex w-full max-w-xs flex-1 flex-col bg-card/90 backdrop-blur-lg h-full shadow-2xl shadow-black/40 border-r border-white/[0.12] animate-in slide-in-from-left duration-200 motion-reduce:animate-none pt-[env(safe-area-inset-top)] pb-[env(safe-area-inset-bottom)]"
            >
              <Sidebar onClose={handleCloseDrawer} showCloseButton={true} />
            </div>
          </div>
        )}

        {/* Main Content Area */}
        <div className="flex flex-col flex-1 md:pl-64 min-w-0">
          {/* Top Navigation */}
          <header className="h-16 flex items-center justify-between px-4 sm:px-6 lg:px-8 border-b border-white/[0.08] bg-background/70 backdrop-blur-md z-10 sticky top-0 shrink-0 pt-[env(safe-area-inset-top)]">
            <div className="flex items-center gap-3">
              {/* Mobile Menu Hamburger Button */}
              <button
                ref={triggerRef}
                type="button"
                onClick={() => setIsMobileMenuOpen(true)}
                aria-label="Open navigation menu"
                aria-expanded={isMobileMenuOpen}
                className="md:hidden flex items-center justify-center min-h-[44px] min-w-[44px] -ml-2 rounded-lg text-muted-foreground hover:text-foreground hover:bg-white/[0.05] transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
              >
                <Menu className="h-5 w-5" />
              </button>

              <Link href="/dashboard" className="md:hidden flex items-center focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary rounded-lg">
                <Image
                  src="/logo.png"
                  alt="Ignition"
                  width={140}
                  height={80}
                  className="h-10 w-auto object-contain"
                  priority
                />
              </Link>
            </div>

            <div className="ml-4 flex items-center md:ml-6">
              <UserMenu />
            </div>
          </header>

          {/* Page Content Viewport */}
          <main id="main-content" className="flex-1 overflow-y-auto overflow-x-hidden">
            <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-8 min-w-0 pb-[calc(2rem+env(safe-area-inset-bottom))]">
              {children}
            </div>
          </main>
        </div>
      </div>
    </AuthGuard>
  )
}
