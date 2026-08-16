import { AppShell } from "@/components/layout/app-shell"
import { ReviewDetailSkeleton } from "@/components/reviews/review-detail-skeleton"

export default function ReviewDetailLoading() {
  return (
    <AppShell>
      <ReviewDetailSkeleton />
    </AppShell>
  )
}
