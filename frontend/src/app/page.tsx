import { LandingNav } from "@/components/landing/landing-nav"
import { HeroSection } from "@/components/landing/hero-section"
import { EditorialBelief } from "@/components/landing/editorial-belief"
import { HowItWorksWorkflow } from "@/components/landing/how-it-works-workflow"
import { CoreCapabilitiesGrid } from "@/components/landing/core-capabilities-grid"
import { EngineeringImpactStrip } from "@/components/landing/engineering-impact-strip"
import { FinalCtaSection } from "@/components/landing/final-cta-section"
import { LandingFooter } from "@/components/landing/landing-footer"

export default function Home() {
  return (
    <div className="min-h-screen bg-surface-dark text-surface-dark-fg selection:bg-primary/30 selection:text-white relative overflow-x-hidden font-sans">
      {/* Global Navigation */}
      <LandingNav />

      {/* Sections alternate dark and warm-cream grounds to break the scroll rhythm. */}
      <main id="main-content">
        {/* Hero with the live product console */}
        <HeroSection />

        {/* Belief statement (cream) */}
        <EditorialBelief />

        {/* Four-stage pipeline */}
        <HowItWorksWorkflow />

        {/* Capabilities, asymmetric 7/5 grid */}
        <CoreCapabilitiesGrid />

        {/* Impact metrics (cream) */}
        <EngineeringImpactStrip />

        {/* Closing CTA with the animated globe */}
        <FinalCtaSection />
      </main>

      <LandingFooter />
    </div>
  )
}
