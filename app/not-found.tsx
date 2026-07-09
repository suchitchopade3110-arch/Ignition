import Link from "next/link"
import { AppShell } from "@/components/app-shell"
import { Search } from "lucide-react"

export default function NotFound() {
  return (
    <AppShell>
      <div className="flex flex-col items-center justify-center min-h-[70vh] text-center px-4">
        <div className="bg-secondary/50 p-6 rounded-full mb-6">
          <Search className="h-12 w-12 text-muted-foreground" />
        </div>
        <h1 className="text-4xl font-bold tracking-tight text-foreground mb-3">404</h1>
        <h2 className="text-xl font-semibold text-foreground mb-4">Page not found</h2>
        <p className="text-muted-foreground max-w-md mb-8">
          The page you are looking for does not exist or has been moved. 
          Please check the URL or return to the dashboard.
        </p>
        <Link 
          href="/dashboard"
          className="inline-flex items-center justify-center rounded-md bg-primary px-6 py-2.5 text-sm font-medium text-primary-foreground hover:bg-primary/90 transition-colors"
        >
          Return to Dashboard
        </Link>
      </div>
    </AppShell>
  )
}
