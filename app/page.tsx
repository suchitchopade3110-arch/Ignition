import { Metadata } from "next"
import { LandingNav } from "@/components/landing/landing-nav"
import { HeroSection } from "@/components/landing/hero-section"
import { ArchitectureSection } from "@/components/landing/architecture-section"
import { FeatureGrid } from "@/components/landing/feature-grid"
import { LiveDemo } from "@/components/landing/live-demo"
import { TechStack } from "@/components/landing/tech-stack"
import { MetricsSection } from "@/components/landing/metrics"
import { FaqSection } from "@/components/landing/faq-section"
import { CtaSection } from "@/components/landing/cta-section"
import { LandingFooter } from "@/components/landing/landing-footer"

export const metadata: Metadata = {
  title: "Ignition | Autonomous Multi-Agent AI Code Review",
  description: "The deterministic multi-agent AI code review platform for modern enterprise engineering teams.",
}

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-background bg-ignition-pattern text-foreground selection:bg-primary/30">
      <LandingNav />
      
      <main>
        <HeroSection />
        
        {/* Trusted By / Metrics Divider */}
        <MetricsSection />
        
        <ArchitectureSection />
        
        <FeatureGrid />
        
        <LiveDemo />
        
        <TechStack />
        
        <FaqSection />
        
        <CtaSection />
      </main>

      <LandingFooter />
    </div>
  )
}
