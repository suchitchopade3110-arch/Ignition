"use client"

import Link from "next/link"
import Image from "next/image"
import { appConfig } from "@/lib/config"

export function LandingFooter() {
  // Backend-served API docs; resolved from config so these are not pinned to localhost.
  const docsUrl = `${appConfig.backendUrl}/docs`
  const redocUrl = `${appConfig.backendUrl}/redoc`

  return (
    <footer className="border-t border-surface-dark-border bg-surface-dark pt-20 pb-12 relative z-10">
      <div className="max-w-7xl mx-auto px-6 sm:px-8 lg:px-12">
        <div className="grid grid-cols-1 md:grid-cols-12 gap-12 pb-16 border-b border-surface-dark-border">
          {/* Left Column: Brand & Subtitle */}
          <div className="md:col-span-4 flex flex-col gap-4">
            <Link
              href="/"
              className="flex items-center focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary rounded-lg w-fit"
            >
              <Image
                src="/logo.png"
                alt="Ignition"
                width={120}
                height={80}
                className="h-8 sm:h-9 w-auto object-contain"
              />
            </Link>
            <p className="text-xs sm:text-sm text-surface-dark-muted leading-relaxed max-w-xs font-sans">
              Autonomous code review <br />
              for engineering teams.
            </p>
          </div>

          {/* Right Column: 4 Columns matching Reference */}
          <div className="md:col-span-8 grid grid-cols-2 sm:grid-cols-4 gap-8 font-sans text-xs">
            {/* Column 1: PRODUCT */}
            <div className="flex flex-col gap-3">
              <span className="font-mono text-[11px] uppercase tracking-wider text-surface-dark-fg font-bold">
                Product
              </span>
              <ul className="space-y-2 text-surface-dark-muted">
                <li>
                  <a href="#how-it-works" className="hover:text-surface-dark-fg transition-colors">
                    How it works
                  </a>
                </li>
                <li>
                  <a href="#capabilities" className="hover:text-surface-dark-fg transition-colors">
                    Features
                  </a>
                </li>
                <li>
                  <Link href="/pricing" className="hover:text-surface-dark-fg transition-colors">
                    Pricing
                  </Link>
                </li>
              </ul>
            </div>

            {/* Column 2: RESOURCES */}
            <div className="flex flex-col gap-3">
              <span className="font-mono text-[11px] uppercase tracking-wider text-surface-dark-fg font-bold">
                Resources
              </span>
              <ul className="space-y-2 text-surface-dark-muted">
                <li>
                  <a
                    href={docsUrl}
                    target="_blank"
                    rel="noreferrer"
                    className="hover:text-surface-dark-fg transition-colors"
                  >
                    Documentation
                  </a>
                </li>
                <li>
                  <a
                    href={redocUrl}
                    target="_blank"
                    rel="noreferrer"
                    className="hover:text-surface-dark-fg transition-colors"
                  >
                    API Reference
                  </a>
                </li>
                <li>
                  <Link href="/changelog" className="hover:text-surface-dark-fg transition-colors">
                    Changelog
                  </Link>
                </li>
              </ul>
            </div>

            {/* Column 3: COMPANY */}
            <div className="flex flex-col gap-3">
              <span className="font-mono text-[11px] uppercase tracking-wider text-surface-dark-fg font-bold">
                Company
              </span>
              <ul className="space-y-2 text-surface-dark-muted">
                <li>
                  <Link href="/security" className="hover:text-surface-dark-fg transition-colors">
                    Security
                  </Link>
                </li>
                <li>
                  <Link href="/privacy" className="hover:text-surface-dark-fg transition-colors">
                    Privacy
                  </Link>
                </li>
                <li>
                  <Link href="/terms" className="hover:text-surface-dark-fg transition-colors">
                    Terms
                  </Link>
                </li>
              </ul>
            </div>

            {/* Column 4: CONNECT */}
            <div className="flex flex-col gap-3">
              <span className="font-mono text-[11px] uppercase tracking-wider text-surface-dark-fg font-bold">
                Connect
              </span>
              <ul className="space-y-2 text-surface-dark-muted">
                <li>
                  <a
                    href="https://github.com"
                    target="_blank"
                    rel="noreferrer"
                    className="hover:text-surface-dark-fg transition-colors"
                  >
                    GitHub
                  </a>
                </li>
                <li>
                  <a href="mailto:support@ignition.dev" className="hover:text-surface-dark-fg transition-colors">
                    Contact
                  </a>
                </li>
                <li>
                  <Link href="/status" className="hover:text-surface-dark-fg transition-colors">
                    Status
                  </Link>
                </li>
              </ul>
            </div>
          </div>
        </div>

        {/* Bottom Social & Copyright Row */}
        <div className="pt-8 flex flex-col sm:flex-row items-center justify-between gap-4 text-xs font-mono text-surface-dark-muted">
          <div>© 2026 Ignition. All rights reserved.</div>

          {/* Social icons matching reference */}
          <div className="flex items-center gap-4 text-surface-dark-muted">
            {/* GitHub */}
            <a
              href="https://github.com"
              target="_blank"
              rel="noreferrer"
              aria-label="GitHub"
              className="hover:text-surface-dark-fg transition-colors"
            >
              <svg className="h-4 w-4 fill-current" viewBox="0 0 24 24">
                <path
                  fillRule="evenodd"
                  d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.531 1.032 1.531 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z"
                  clipRule="evenodd"
                />
              </svg>
            </a>

            {/* Twitter / X */}
            <a
              href="https://twitter.com"
              target="_blank"
              rel="noreferrer"
              aria-label="Twitter"
              className="hover:text-surface-dark-fg transition-colors"
            >
              <svg className="h-4 w-4 fill-current" viewBox="0 0 24 24">
                <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z" />
              </svg>
            </a>

            {/* LinkedIn */}
            <a
              href="https://linkedin.com"
              target="_blank"
              rel="noreferrer"
              aria-label="LinkedIn"
              className="hover:text-surface-dark-fg transition-colors"
            >
              <svg className="h-4 w-4 fill-current" viewBox="0 0 24 24">
                <path d="M19 3a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h14m-.5 15.5v-5.3a3.26 3.26 0 0 0-3.26-3.26c-.85 0-1.84.52-2.28 1.3v-1.11h-2.79v8.37h2.79v-4.93c0-.77.62-1.4 1.39-1.4a1.4 1.4 0 0 1 1.4 1.4v4.93h2.75M6.46 8.76a1.68 1.68 0 0 0 1.68-1.68c0-.93-.75-1.69-1.68-1.69a1.69 1.69 0 0 0-1.69 1.69c0 .93.76 1.68 1.69 1.68m1.39 9.94v-8.37H5.07v8.37h2.78z" />
              </svg>
            </a>
          </div>
        </div>
      </div>
    </footer>
  )
}
