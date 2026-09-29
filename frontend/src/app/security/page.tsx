import { Metadata } from "next"
import { LandingNav } from "@/components/landing/landing-nav"
import { LandingFooter } from "@/components/landing/landing-footer"

export const metadata: Metadata = {
  title: "Security | Ignition",
  description: "How Ignition protects your code, tokens, and webhook traffic — and how to report a vulnerability.",
}

const practices = [
  {
    title: "Webhook signatures are verified on every request",
    body: "Every inbound GitHub webhook is checked against its X-Hub-Signature-256 header using HMAC-SHA256 before it's processed. Unsigned or incorrectly signed requests are rejected with a 401 — nothing reaches the review pipeline without proving it came from GitHub.",
  },
  {
    title: "Zero-downtime secret rotation",
    body: "The webhook secret supports a grace-period rotation: both the outgoing and incoming secret are accepted during a rotation window, so credentials can be replaced without dropping webhook deliveries.",
  },
  {
    title: "CSRF protection on session-authenticated routes",
    body: "State-changing API routes that rely on cookie authentication (repo settings, HITL approve/reject) use a double-submit CSRF token in addition to a SameSite=Lax session cookie. Routes authenticated by webhook signature instead of cookies are not exposed to CSRF in the first place, since there's no ambient cookie auth to forge.",
  },
  {
    title: "Least-privilege GitHub App access",
    body: "Ignition authenticates to your repositories as a GitHub App, using short-lived installation tokens rather than a long-lived personal access token. Access is scoped to the repositories you explicitly install the app on.",
  },
  {
    title: "Secrets are never in source control",
    body: "Credentials (GitHub App keys, webhook secrets, OAuth secrets, database keys, LLM API keys) live in environment configuration, not in the repository. Container builds copy only the application code they need — never the environment file.",
  },
]

export default function SecurityPage() {
  return (
    <div className="min-h-screen bg-surface-dark text-surface-dark-fg selection:bg-primary/30 selection:text-white relative overflow-x-hidden font-sans flex flex-col">
      <LandingNav />

      <main id="main-content" className="flex-1 px-6 py-32">
        <div className="max-w-3xl mx-auto">
          <h1 className="text-h2 text-surface-dark-fg mb-4">Security</h1>
          <p className="text-sm text-surface-dark-muted leading-relaxed mb-16 max-w-xl">
            Ignition reads and comments on your pull requests, which means it needs access to your
            code. Here's what we actually do to protect that access — and how to reach us if you
            find a problem.
          </p>

          <section className="mb-16">
            <h2 className="text-lg font-semibold text-surface-dark-fg mb-6">
              How your data is protected
            </h2>
            <div className="flex flex-col gap-8">
              {practices.map((item) => (
                <div
                  key={item.title}
                  className="border-l-2 border-surface-dark-border-strong pl-5"
                >
                  <h3 className="text-sm font-semibold text-surface-dark-fg mb-1.5">
                    {item.title}
                  </h3>
                  <p className="text-sm text-surface-dark-muted leading-relaxed">{item.body}</p>
                </div>
              ))}
            </div>
          </section>

          <section className="mb-16">
            <h2 className="text-lg font-semibold text-surface-dark-fg mb-4">
              Reporting a vulnerability
            </h2>
            <p className="text-sm text-surface-dark-muted leading-relaxed mb-3">
              If you find a security issue in Ignition, please don't open a public GitHub issue.
              Email{" "}
              <a
                href="mailto:suchitchopade3110@gmail.com"
                className="text-primary hover:text-primary-hover underline underline-offset-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary rounded"
              >
                suchitchopade3110@gmail.com
              </a>{" "}
              with a description and reproduction steps. We aim to acknowledge reports within 3
              business days.
            </p>
            <p className="text-sm text-surface-dark-muted leading-relaxed">
              Full scope and disclosure terms are in our{" "}
              <a
                href="https://github.com/suchitchopade3110-arch/Ignition/blob/main/SECURITY.md"
                target="_blank"
                rel="noreferrer"
                className="text-primary hover:text-primary-hover underline underline-offset-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary rounded"
              >
                SECURITY.md
              </a>
              .
            </p>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-surface-dark-fg mb-4">What's next</h2>
            <p className="text-sm text-surface-dark-muted leading-relaxed">
              This page describes the mechanisms in place today. It is not a compliance
              certification (SOC 2, ISO 27001, etc.) — we're an early-stage product and don't
              claim one. If a formal certification matters for your organization, reach out and
              we'll let you know where things stand.
            </p>
          </section>
        </div>
      </main>

      <LandingFooter />
    </div>
  )
}
