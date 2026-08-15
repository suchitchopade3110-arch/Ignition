"use client"

import { useToast } from "@/hooks/use-toast"
import { motion, AnimatePresence } from "framer-motion"
import { CheckCircle2, XCircle, AlertTriangle, Info, X } from "lucide-react"
import { cn } from "@/lib/utils"

export function Toaster() {
  const { toasts, dismiss } = useToast()

  return (
    <div className="fixed bottom-0 right-0 z-[100] flex max-h-screen w-full flex-col-reverse p-4 sm:bottom-0 sm:right-0 sm:top-auto sm:flex-col md:max-w-[420px] gap-2 pointer-events-none">
      <AnimatePresence>
        {toasts.map((toast) => {
          let Icon = Info
          let colorClass = "text-foreground bg-card border-border"
          let iconColor = "text-muted-foreground"

          if (toast.type === "success") {
            Icon = CheckCircle2
            colorClass = "border-success/30 bg-card"
            iconColor = "text-success"
          } else if (toast.type === "error") {
            Icon = XCircle
            colorClass = "border-critical/30 bg-critical/10"
            iconColor = "text-critical"
          } else if (toast.type === "warning") {
            Icon = AlertTriangle
            colorClass = "border-warning/30 bg-warning/10"
            iconColor = "text-warning"
          } else if (toast.type === "info") {
            Icon = Info
            colorClass = "border-primary/30 bg-primary/10"
            iconColor = "text-primary"
          }

          return (
            <motion.div
              key={toast.id}
              layout
              initial={{ opacity: 0, y: 50, scale: 0.9 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, scale: 0.9, transition: { duration: 0.2 } }}
              className={cn(
                "group pointer-events-auto relative flex w-full items-center justify-between space-x-4 overflow-hidden rounded-md border p-4 shadow-lg transition-all",
                colorClass
              )}
            >
              <div className="flex items-start gap-3 flex-1">
                <Icon className={cn("mt-0.5 h-5 w-5 shrink-0", iconColor)} />
                <div className="flex flex-col gap-1">
                  {toast.title && <div className="text-sm font-medium">{toast.title}</div>}
                  {toast.description && (
                    <div className="text-sm opacity-90">{toast.description}</div>
                  )}
                </div>
              </div>
              <button
                onClick={() => dismiss(toast.id)}
                className="absolute right-2 top-2 rounded-md p-1 opacity-0 transition-opacity hover:bg-secondary group-hover:opacity-100 focus:opacity-100 focus:outline-none focus:ring-2"
              >
                <X className="h-4 w-4" />
              </button>
            </motion.div>
          )
        })}
      </AnimatePresence>
    </div>
  )
}
