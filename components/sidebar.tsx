"use client"

import Link from "next/link"
import Image from "next/image"
import { usePathname } from "next/navigation"
import { LayoutDashboard, GitBranch, MessageSquare, ShieldCheck, Activity } from "lucide-react"
import { cn } from "@/lib/utils"
import { motion } from "framer-motion"

const navigation = [
  { name: "Dashboard", href: "/dashboard", icon: LayoutDashboard },
  { name: "Repositories", href: "/repos", icon: GitBranch },
  { name: "Code Reviews", href: "/reviews", icon: MessageSquare },
  { name: "HITL Approvals", href: "/hitl", icon: ShieldCheck },
  { name: "Ledger", href: "/ledger", icon: Activity },
]

export function Sidebar() {
  const pathname = usePathname()

  return (
    <div className="flex h-full flex-col">
      <div className="flex h-16 shrink-0 items-center px-6 bg-card border-b border-border">
        <Link href="/dashboard" className="flex items-center gap-3">
          <div className="relative h-8 w-8 flex items-center justify-center">
            <Image 
              src="/logo.svg" 
              alt="Ignition" 
              fill
              className="object-contain"
              priority
            />
          </div>
          <span className="text-xl font-bold tracking-tight text-foreground">Ignition</span>
        </Link>
      </div>
      <div className="flex flex-1 flex-col overflow-y-auto pt-6 px-3">
        <nav className="flex-1 space-y-1">
          {navigation.map((item) => {
            const isActive = pathname?.startsWith(item.href)
            return (
              <Link
                key={item.name}
                href={item.href}
                className={cn(
                  isActive
                    ? "bg-secondary text-primary"
                    : "text-muted-foreground hover:bg-secondary/50 hover:text-foreground",
                  "group flex items-center px-3 py-2 text-sm font-medium rounded-md relative transition-colors duration-200"
                )}
              >
                <item.icon
                  className={cn(
                    isActive ? "text-primary" : "text-muted-foreground group-hover:text-foreground",
                    "mr-3 flex-shrink-0 h-5 w-5 transition-colors duration-200"
                  )}
                  aria-hidden="true"
                />
                {item.name}
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
      <div className="p-4 border-t border-border">
        <div className="flex items-center gap-3">
          <div className="h-8 w-8 rounded-full bg-secondary flex items-center justify-center text-xs font-medium text-foreground">
            SE
          </div>
          <div className="flex flex-col">
            <span className="text-sm font-medium text-foreground">System Engineer</span>
            <span className="text-xs text-muted-foreground">Pro Plan</span>
          </div>
        </div>
      </div>
    </div>
  )
}
