import { Metadata } from "next"
import { ComingSoonPage } from "@/components/landing/coming-soon-page"

export const metadata: Metadata = {
  title: "Status | Ignition",
  description: "Ignition system status — coming soon.",
}

export default function StatusPage() {
  return <ComingSoonPage title="Status" />
}
