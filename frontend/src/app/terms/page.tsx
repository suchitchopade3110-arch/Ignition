import { Metadata } from "next"
import { ComingSoonPage } from "@/components/landing/coming-soon-page"

export const metadata: Metadata = {
  title: "Terms | Ignition",
  description: "Ignition terms of service — coming soon.",
}

export default function TermsPage() {
  return <ComingSoonPage title="Terms" />
}
