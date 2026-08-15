import { Metadata } from "next"
import { notFound } from "next/navigation"
import { AppShell } from "@/components/layout/app-shell"
import { ReviewDetailView } from "@/components/reviews/review-detail-view"
import { apiClient } from "@/lib/api-client"

export const dynamic = "force-dynamic"

export const metadata: Metadata = {
  title: "Review Details | Ignition",
  description: "View AI Code Review details and findings",
}

export default async function ReviewDetailPage(props: { params: Promise<{ id: string }> }) {
  const params = await props.params
  const review = await apiClient.getReview(params.id)

  if (!review) {
    notFound()
  }

  return (
    <AppShell>
      <ReviewDetailView reviewId={params.id} initialData={review} />
    </AppShell>
  )
}
