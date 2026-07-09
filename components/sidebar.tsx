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
        <Link href="/" className="flex items-center h-full">
          <div className="relative h-14 w-20 flex items-center justify-center">
            <Image 
              src="/logo-full.png" 
              alt="Ignition" 
              fill
              className="object-contain scale-[2]"
              priority
            />
          </div>
          <span className="text-xl font-bold tracking-tight text-transparent bg-clip-text bg-gradient-to-r from-primary to-blue-400">IGNITION</span>
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
                    ? "bg-secondary text-primary shadow-[0_0_15px_rgba(255,69,0,0.15)]"
                    : "text-muted-foreground hover:bg-secondary/80 hover:text-foreground",
                  "group flex items-center px-3 py-2 text-sm font-medium rounded-md relative transition-all duration-300 hover:scale-[1.03] hover:shadow-[0_0_15px_rgba(255,69,0,0.4)] hover:z-10"
                )}
              >
                <item.icon
                  className={cn(
                    isActive ? "text-primary" : "text-muted-foreground group-hover:text-primary",
                    "mr-3 flex-shrink-0 h-5 w-5 transition-colors duration-300"
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
