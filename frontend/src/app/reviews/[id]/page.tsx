import { Metadata } from "next"
import { AppShell } from "@/components/layout/app-shell"
import { ReviewDetailView } from "@/components/reviews/review-detail-view"

export const metadata: Metadata = {
  title: "Review Details | Ignition",
  description: "View AI Code Review details and findings",
}

export default async function ReviewDetailPage(props: { params: Promise<{ id: string }> }) {
  const params = await props.params

  // Fetched client-side by ReviewDetailView via useReview(), not here. This
  // endpoint requires the session cookie, and a server component's fetch has
  // no access to it (credentials: "include" only affects browser-initiated
  // requests) — a server-side call here 401s on every real visit even though
  // the visitor is signed in.
  return (
    <AppShell>
      <ReviewDetailView reviewId={params.id} />
    </AppShell>
  )
}
