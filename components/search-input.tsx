import { Search } from "lucide-react"
import { cn } from "@/lib/utils"

export type SearchInputProps = React.InputHTMLAttributes<HTMLInputElement>

export function SearchInput({ className, ...props }: SearchInputProps) {
  return (
    <div className={cn("relative", className)}>
      <div className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3">
        <Search className="h-4 w-4 text-muted-foreground" aria-hidden="true" />
      </div>
      <input
        type="search"
        className="block w-full rounded-md border border-border bg-card/50 py-2 pl-10 pr-3 text-sm text-foreground placeholder:text-muted-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary sm:text-sm transition-colors"
        {...props}
      />
    </div>
  )
}
