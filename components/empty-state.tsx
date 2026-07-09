import { LucideIcon } from "lucide-react"

interface EmptyStateProps {
  icon: LucideIcon
  title: string
  description: string
  action?: React.ReactNode
}

export function EmptyState({ icon: Icon, title, description, action }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-border bg-card/50 px-6 py-12 text-center h-full min-h-[300px]">
      <div className="flex h-12 w-12 items-center justify-center rounded-full bg-secondary mb-4">
        <Icon className="h-6 w-6 text-muted-foreground" />
      </div>
      <h3 className="text-lg font-medium text-foreground">{title}</h3>
      <p className="mt-2 text-sm text-muted-foreground max-w-sm mx-auto mb-6">
        {description}
      </p>
      {action && <div>{action}</div>}
    </div>
  )
}
