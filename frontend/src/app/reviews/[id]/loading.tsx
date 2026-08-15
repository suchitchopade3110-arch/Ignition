import { AppShell } from "@/components/layout/app-shell"
import { CardSkeleton, Skeleton } from "@/components/ui/loading-skeleton"

export default function ReviewDetailLoading() {
  return (
    <AppShell>
      {/* Header skeleton */}
      <div className="mb-8 border-b border-border pb-6 space-y-4">
        <div className="flex items-center gap-3">
          <Skeleton className="h-8 w-72" />
          <Skeleton className="h-6 w-20 rounded-full" />
        </div>
        <div className="flex gap-4">
          <Skeleton className="h-6 w-32 rounded-md" />
          <Skeleton className="h-6 w-28 rounded-md" />
          <Skeleton className="h-6 w-24 rounded-md" />
        </div>
      </div>

      {/* Summary cards skeleton */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-10">
        <CardSkeleton />
        <CardSkeleton />
        <CardSkeleton />
        <CardSkeleton />
      </div>

      {/* Main content area */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <div className="lg:col-span-2 space-y-6">
          <div className="bg-card p-6 rounded-xl border border-border space-y-4">
            <Skeleton className="h-6 w-48" />
            <Skeleton className="h-20 w-full" />
            <Skeleton className="h-20 w-full" />
          </div>
        </div>
        <div>
          <div className="bg-card p-6 rounded-xl border border-border space-y-4">
            <Skeleton className="h-6 w-36" />
            <Skeleton className="h-32 w-full" />
          </div>
        </div>
      </div>
    </AppShell>
  )
}
