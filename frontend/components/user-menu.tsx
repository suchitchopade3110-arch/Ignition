"use client"

import { User, Settings } from "lucide-react"

export function UserMenu() {
  return (
    <div className="relative flex items-center gap-4">
      {/* Search Trigger or Notifications could go here */}
      <button className="text-muted-foreground hover:text-foreground transition-colors">
        <Settings className="h-5 w-5" />
      </button>
      
      {/* Simple Avatar Dropdown Mock */}
      <button className="flex items-center justify-center h-8 w-8 rounded-full bg-secondary border border-border overflow-hidden focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2 focus:ring-offset-background transition-all">
        <User className="h-4 w-4 text-muted-foreground" />
      </button>
    </div>
  )
}
