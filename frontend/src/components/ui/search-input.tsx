import { Search } from "lucide-react"
import { cn } from "@/lib/utils"

export type SearchInputProps = React.InputHTMLAttributes<HTMLInputElement>

export function SearchInput({ className, ...props }: SearchInputProps) {
  return (
    <div className={cn("relative", className)}>
      <div className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3.5">
        <Search className="h-4 w-4 text-muted-foreground" aria-hidden="true" />
      </div>
      <input
        type="search"
        className="block w-full min-h-[44px] rounded-lg border border-border bg-card/50 py-2.5 pl-10 pr-3.5 text-xs sm:text-sm text-foreground placeholder:text-muted-foreground focus-visible:border-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-1 focus-visible:ring-offset-background transition-colors"
        {...props}
      />
    </div>
  )
}
