import { cn } from "@/lib/utils"
import { AlertCircle, AlertTriangle, Info, CheckCircle2, Shield, LucideIcon } from "lucide-react"
import { SeverityLevel } from "@/lib/types"

interface SeverityBadgeProps {
  level: SeverityLevel
  className?: string
}

const config: Record<SeverityLevel, { label: string, styles: string, icon: LucideIcon }> = {
  info: {
    label: "Info",
    styles: "bg-blue-500/10 text-blue-500 border-blue-500/20",
    icon: Info
  },
  none: {
    label: "None",
    styles: "bg-secondary text-muted-foreground border-border",
    icon: Shield
  },
  low: {
    label: "Low",
    styles: "bg-blue-500/10 text-blue-500 border-blue-500/20",
    icon: Info
  },
  medium: {
    label: "Medium",
    styles: "bg-warning/10 text-warning border-warning/20",
    icon: AlertTriangle
  },
  warning: {
    label: "Warning",
    styles: "bg-warning/10 text-warning border-warning/20",
    icon: AlertTriangle
  },
  high: {
    label: "High",
    styles: "bg-danger/10 text-danger border-danger/20",
    icon: AlertCircle
  },
  danger: {
    label: "Danger",
    styles: "bg-danger/10 text-danger border-danger/20",
    icon: AlertCircle
  },
  critical: {
    label: "Critical",
    styles: "bg-critical/10 text-critical border-critical/20",
    icon: AlertCircle
  },
  success: {
    label: "Passed",
    styles: "bg-success/10 text-success border-success/20",
    icon: CheckCircle2
  }
}

export function SeverityBadge({ level, className }: SeverityBadgeProps) {
  const { label, styles, icon: Icon } = config[level] || config.info

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
