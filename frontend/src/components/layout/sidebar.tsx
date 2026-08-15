"use client"

import Link from "next/link"
import Image from "next/image"
import { usePathname } from "next/navigation"
import { LayoutDashboard, GitBranch, MessageSquare, ShieldCheck, Activity, X } from "lucide-react"
import { cn } from "@/lib/utils"
import { motion } from "framer-motion"
import { useAuth } from "@/lib/auth-context"

const navigation = [
  { name: "Dashboard", href: "/dashboard", icon: LayoutDashboard },
  { name: "Repositories", href: "/repos", icon: GitBranch },
  { name: "Code Reviews", href: "/reviews", icon: MessageSquare },
  { name: "HITL Approvals", href: "/hitl", icon: ShieldCheck },
  { name: "Ledger", href: "/ledger", icon: Activity },
]

interface SidebarProps {
  onClose?: () => void
  showCloseButton?: boolean
}

export function Sidebar({ onClose, showCloseButton = false }: SidebarProps) {
  const pathname = usePathname()
  const { user } = useAuth()

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
    <div className="flex h-full flex-col bg-card/65 backdrop-blur-md border-r border-white/[0.08]">
      <div className="flex h-16 shrink-0 items-center justify-between px-6 border-b border-white/[0.06]">
        <Link
          href="/dashboard"
          onClick={onClose}
          className="flex items-center focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary rounded-lg p-1"
        >
          <Image
            src="/logo.png"
            alt="Ignition"
            width={150}
            height={100}
            className="h-11 w-auto object-contain"
            priority
          />
        </Link>

        {showCloseButton && onClose && (
          <button
            type="button"
            onClick={onClose}
            aria-label="Close sidebar"
            className="flex items-center justify-center min-h-[44px] min-w-[44px] rounded-lg text-muted-foreground hover:text-foreground hover:bg-white/[0.05] transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
          >
            <X className="h-5 w-5" />
          </button>
        )}
      </div>

      <div className="flex flex-1 flex-col overflow-y-auto pt-6 px-3">
        <nav className="flex-1 space-y-1.5" aria-label="Main navigation">
          {navigation.map((item) => {
            const isActive = pathname?.startsWith(item.href)
            return (
              <Link
                key={item.name}
                href={item.href}
                onClick={onClose}
                className={cn(
                  isActive
                    ? "bg-white/[0.05] text-primary font-medium border border-white/[0.08]"
                    : "text-muted-foreground hover:bg-white/[0.03] hover:text-foreground",
                  "group flex items-center min-h-[44px] px-3.5 py-2.5 text-sm rounded-lg relative transition-colors duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 focus-visible:ring-offset-card"
                )}
              >
                <item.icon
                  className={cn(
                    isActive ? "text-primary" : "text-muted-foreground group-hover:text-foreground",
                    "mr-3 shrink-0 h-5 w-5 transition-colors duration-200"
                  )}
                  aria-hidden="true"
                />
                <span>{item.name}</span>
                {isActive && (
                  <motion.div
                    layoutId="sidebar-active"
                    className="absolute left-0 top-0 bottom-0 w-1 bg-primary rounded-r-full"
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ type: "spring", stiffness: 300, damping: 30 }}
                  />
                )}
              </Link>
            )
          })}
        </nav>
      </div>

      <div className="p-4 border-t border-white/[0.06] bg-transparent">
        <div className="flex items-center gap-3">
          <div className="h-8 w-8 rounded-full bg-secondary/70 flex items-center justify-center text-xs font-semibold text-foreground overflow-hidden border border-white/[0.08]">
            {user?.avatar_url ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img src={user.avatar_url} alt={user.name || user.login} className="h-full w-full object-cover" />
            ) : (
              <span>{initials}</span>
            )}
          </div>
          <div className="flex flex-col min-w-0">
            <span className="text-sm font-medium text-foreground truncate">
              {user?.name || user?.login || "System Engineer"}
            </span>
            <span className="text-xs text-muted-foreground truncate">
              {user ? `@${user.login}` : "Enterprise Pro"}
            </span>
          </div>
        </div>
      </div>
    </div>
  )
}
