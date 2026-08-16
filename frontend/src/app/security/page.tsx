import { Metadata } from "next"
import { ComingSoonPage } from "@/components/landing/coming-soon-page"

export const metadata: Metadata = {
  title: "Security | Ignition",
  description: "Ignition security practices — coming soon.",
}

export default function SecurityPage() {
  return <ComingSoonPage title="Security" />
}
