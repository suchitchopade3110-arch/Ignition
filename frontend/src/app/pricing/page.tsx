import { Metadata } from "next"
import { ComingSoonPage } from "@/components/landing/coming-soon-page"

export const metadata: Metadata = {
  title: "Pricing | Ignition",
  description: "Ignition pricing — coming soon.",
}

export default function PricingPage() {
  return <ComingSoonPage title="Pricing" />
}
