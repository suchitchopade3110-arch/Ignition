import { cn } from "@/lib/utils"
import { ReviewStatusType } from "@/lib/types"
import {
  Clock,
  PlayCircle,
  PauseCircle,
  UserCog,
  CheckCircle2,
  XCircle,
  Ban
} from "lucide-react"

interface StatusBadgeProps {
  status: ReviewStatusType
  className?: string
}

const config = {
  queued: { label: "Queued", icon: Clock, styles: "bg-secondary text-muted-foreground border-border" },
  running: { label: "Running", icon: PlayCircle, styles: "bg-primary/10 text-primary border-primary/20" },
  paused: { label: "Paused", icon: PauseCircle, styles: "bg-warning/10 text-warning border-warning/20" },
  waiting_hitl: { label: "Waiting HITL", icon: UserCog, styles: "bg-warning/10 text-warning border-warning/20" },
  completed: { label: "Completed", icon: CheckCircle2, styles: "bg-success/10 text-success border-success/20" },
  failed: { label: "Failed", icon: XCircle, styles: "bg-critical/10 text-critical border-critical/20" },
  cancelled: { label: "Cancelled", icon: Ban, styles: "bg-secondary text-muted-foreground border-border" },
}

export function StatusBadge({ status, className }: StatusBadgeProps) {
  const { label, styles, icon: Icon } = config[status] || config.queued

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium border",
        styles,
        className
      )}
    >
      <Icon className={cn("h-3.5 w-3.5", status === "running" && "animate-pulse")} />
      {label}
    </span>
  )
}
