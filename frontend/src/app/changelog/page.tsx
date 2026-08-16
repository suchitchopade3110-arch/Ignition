import { Metadata } from "next"
import { ComingSoonPage } from "@/components/landing/coming-soon-page"

export const metadata: Metadata = {
  title: "Changelog | Ignition",
  description: "Ignition changelog — coming soon.",
}

export default function ChangelogPage() {
  return <ComingSoonPage title="Changelog" />
}
