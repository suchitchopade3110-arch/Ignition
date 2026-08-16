import { Metadata } from "next"
import { ComingSoonPage } from "@/components/landing/coming-soon-page"

export const metadata: Metadata = {
  title: "Privacy | Ignition",
  description: "Ignition privacy policy — coming soon.",
}

export default function PrivacyPage() {
  return <ComingSoonPage title="Privacy" />
}
