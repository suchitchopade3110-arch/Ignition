import Link from "next/link"
import { Clock, ArrowLeft } from "lucide-react"
import { LandingNav } from "./landing-nav"
import { LandingFooter } from "./landing-footer"

/**
 * Shared shell for footer links that don't have a real destination yet
 * (Pricing, Changelog, Security, Privacy, Terms, Status). Renders an
 * honest "not live yet" page instead of either a dead link or fabricated
 * content — this is deliberately not a placeholder Privacy Policy or
 * Terms of Service; inventing real-looking legal text would be actively
 * misleading, not just incomplete.
 */
export function ComingSoonPage({ title }: { title: string }) {
  return (
    <div className="min-h-screen bg-surface-dark text-surface-dark-fg selection:bg-primary/30 selection:text-white relative overflow-x-hidden font-sans flex flex-col">
      <LandingNav />

      <main id="main-content" className="flex-1 flex items-center justify-center px-6 py-32">
        <div className="max-w-md text-center flex flex-col items-center">
          <div className="h-12 w-12 rounded-full bg-surface-dark-panel border border-surface-dark-border-strong flex items-center justify-center mb-6">
            <Clock className="h-5 w-5 text-primary" />
          </div>
          <h1 className="text-h2 text-surface-dark-fg mb-3">{title}</h1>
          <p className="text-sm text-surface-dark-muted leading-relaxed mb-8">
            This page isn&apos;t live yet. We&apos;d rather tell you that plainly than show you
            something that isn&apos;t real.
          </p>
          <Link
            href="/"
            className="group inline-flex items-center gap-2 text-xs font-mono uppercase tracking-wider text-surface-dark-fg hover:text-primary transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary rounded-md px-2 py-1"
          >
            <ArrowLeft className="h-3.5 w-3.5 transition-transform group-hover:-translate-x-0.5" />
            Back to home
          </Link>
        </div>
      </main>

      <LandingFooter />
    </div>
  )
}
