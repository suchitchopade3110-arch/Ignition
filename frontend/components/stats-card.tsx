import { LucideIcon } from "lucide-react"
import { cn } from "@/lib/utils"

interface StatsCardProps {
  title: string
  value: string | number
  description?: string
  icon: LucideIcon
  trend?: {
    value: number
    label: string
    isPositive: boolean
  }
}

export function StatsCard({ title, value, description, icon: Icon, trend }: StatsCardProps) {
  return (
    <div className="rounded-xl border border-border bg-card p-6 shadow-sm flex flex-col">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-medium text-muted-foreground">{title}</h3>
        <Icon className="h-4 w-4 text-muted-foreground" />
      </div>
      <div className="mt-4 flex items-baseline gap-2">
        <span className="text-3xl font-bold tracking-tight text-foreground">{value}</span>
      </div>
      {(trend || description) && (
        <div className="mt-2 text-xs">
          {trend ? (
            <div className="flex items-center gap-1.5">
              <span className={cn("font-medium", trend.isPositive ? "text-success" : "text-critical")}>
                {trend.isPositive ? "+" : "-"}{Math.abs(trend.value)}%
              </span>
              <span className="text-muted-foreground">{trend.label}</span>
            </div>
          ) : (
            <span className="text-muted-foreground">{description}</span>
          )}
        </div>
      )}
    </div>
  )
}
