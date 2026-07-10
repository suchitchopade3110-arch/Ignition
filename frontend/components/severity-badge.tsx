import { cn } from "@/lib/utils"
import { AlertCircle, AlertTriangle, Info, Shield, LucideIcon } from "lucide-react"
import { SeverityLevel } from "@/lib/types"

interface SeverityBadgeProps {
  level: SeverityLevel
  className?: string
}

const config: Record<SeverityLevel, { label: string, styles: string, icon: LucideIcon }> = {
  none: {
    label: "None",
    styles: "bg-secondary text-muted-foreground border-border",
    icon: Shield
  },
  low: {
    label: "Low",
    styles: "bg-info/10 text-info border-info/20",
    icon: Info
  },
  medium: {
    label: "Medium",
    styles: "bg-warning/10 text-warning border-warning/20",
    icon: AlertTriangle
  },
  high: {
    label: "High",
    styles: "bg-danger/10 text-danger border-danger/20",
    icon: AlertCircle
  },
  critical: {
    label: "Critical",
    styles: "bg-critical/10 text-critical border-critical/20",
    icon: AlertCircle
  }
}

export function SeverityBadge({ level, className }: SeverityBadgeProps) {
  const badgeConfig = config[level] || config.none
  const { label, styles, icon: Icon } = badgeConfig

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-xs font-medium border",
        styles,
        className
      )}
    >
      <Icon className="h-3 w-3" />
      {label}
    </span>
  )
}
