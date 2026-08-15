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

      {/* Main Content Sections */}
      <main id="main-content">
        {/* 01 / Hero Section with Real Product Console */}
        <HeroSection />

        {/* Editorial Belief Section (Warm Off-White) */}
        <EditorialBelief />

        {/* 02 / How Ignition Works (4-Stage Pipeline) */}
        <HowItWorksWorkflow />

        {/* 03 / Core Capabilities Grid */}
        <CoreCapabilitiesGrid />

        {/* 04 / Engineering Impact Metrics (Warm Off-White) */}
        <EngineeringImpactStrip />

        {/* 05 / Final CTA with Animated Technical Globe */}
        <FinalCtaSection />
      </main>

      <LandingFooter />
    </div>
  )
}
