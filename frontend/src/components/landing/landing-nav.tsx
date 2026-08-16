"use client"

import { useState, useEffect } from "react"
import Link from "next/link"
import Image from "next/image"
import { motion } from "framer-motion"
import { Menu, X, ArrowRight } from "lucide-react"

export function LandingNav() {
  const [isScrolled, setIsScrolled] = useState(false)
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false)

  useEffect(() => {
    const handleScroll = () => {
      setIsScrolled(window.scrollY > 20)
    }
    window.addEventListener("scroll", handleScroll)
    return () => window.removeEventListener("scroll", handleScroll)
  }, [])

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape" && isMobileMenuOpen) {
        setIsMobileMenuOpen(false)
      }
    }
    window.addEventListener("keydown", handleKeyDown)
    return () => window.removeEventListener("keydown", handleKeyDown)
  }, [isMobileMenuOpen])

  return (
    <>
      <motion.header
        initial={{ y: -80, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        transition={{ duration: 0.4, ease: "easeOut" }}
        className={`fixed top-0 left-0 right-0 z-50 transition-all duration-300 ${
          isScrolled
            ? "bg-surface-dark/85 backdrop-blur-md border-b border-surface-dark-border py-3.5 shadow-md shadow-black/40"
            : "bg-transparent py-5"
        }`}
      >
        <div className="max-w-7xl mx-auto px-6 sm:px-8 lg:px-12">
          <div className="flex items-center justify-between">
            {/* Brand Logo - Big and Clearly Visible */}
            <Link
              href="/"
              className="flex items-center focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary rounded-lg group"
              aria-label="Ignition Home"
            >
              <Image
                src="/logo.png"
                alt="Ignition"
                width={220}
                height={120}
                className="h-11 sm:h-12 md:h-14 w-auto object-contain transition-transform group-hover:scale-[1.02]"
                priority
              />
            </Link>

            {/* Desktop Navigation Links matching Reference */}
            <nav className="hidden md:flex items-center gap-7 text-xs font-sans font-medium text-surface-dark-muted">
              <a
                href="#capabilities"
                className="hover:text-surface-dark-fg transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-primary rounded px-1"
              >
                Product
              </a>
              <a
                href="#how-it-works"
                className="hover:text-surface-dark-fg transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-primary rounded px-1"
              >
                How it works
              </a>
              <a
                href="#security"
                className="hover:text-surface-dark-fg transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-primary rounded px-1"
              >
                Security
              </a>
              <a
                href="https://github.com"
                target="_blank"
                rel="noreferrer"
                className="hover:text-surface-dark-fg transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-primary rounded px-1"
              >
                GitHub
              </a>
              <a
                href="http://localhost:8000/docs"
                target="_blank"
                rel="noreferrer"
                className="hover:text-surface-dark-fg transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-primary rounded px-1"
              >
                Docs
              </a>
            </nav>

            {/* Desktop Action Area matching Reference */}
            <div className="hidden md:flex items-center gap-6">
              <Link
                href="/login"
                className="text-xs font-sans font-medium text-surface-dark-muted hover:text-surface-dark-fg transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-primary rounded px-1"
              >
                Sign in
              </Link>
              <Link
                href="/login"
                className="group flex items-center gap-2 px-4 py-2 bg-primary hover:bg-primary-hover text-white text-xs font-mono uppercase tracking-wider font-bold rounded-lg transition-all shadow-[0_0_15px_rgba(255,69,0,0.25)] hover:shadow-[0_0_20px_rgba(255,69,0,0.4)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
              >
                <span>Connect GitHub</span>
                <ArrowRight className="w-3.5 h-3.5 transition-transform group-hover:translate-x-0.5" />
              </Link>
            </div>

            {/* Mobile Menu Trigger */}
            <button
              type="button"
              className="md:hidden p-2 min-h-[44px] min-w-[44px] flex items-center justify-center text-surface-dark-muted hover:text-surface-dark-fg rounded-lg hover:bg-white/[0.05] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary relative z-50"
              onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
              aria-label="Toggle navigation menu"
              aria-expanded={isMobileMenuOpen}
            >
              {isMobileMenuOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
            </button>
          </div>
        </div>
      </motion.header>

      {/* Mobile Menu Slideout */}
      {isMobileMenuOpen && (
        <div className="fixed inset-0 z-50 bg-surface-dark/95 backdrop-blur-xl md:hidden pt-28 px-6 pb-12 border-b border-surface-dark-border flex flex-col justify-between overflow-y-auto">
          <div className="flex flex-col gap-6">
            <a
              href="#capabilities"
              onClick={() => setIsMobileMenuOpen(false)}
              className="text-lg font-sans font-medium text-surface-dark-fg hover:text-primary transition-colors py-2 border-b border-white/[0.04]"
            >
              Product
            </a>
            <a
              href="#how-it-works"
              onClick={() => setIsMobileMenuOpen(false)}
              className="text-lg font-sans font-medium text-surface-dark-fg hover:text-primary transition-colors py-2 border-b border-white/[0.04]"
            >
              How it works
            </a>
            <a
              href="#security"
              onClick={() => setIsMobileMenuOpen(false)}
              className="text-lg font-sans font-medium text-surface-dark-fg hover:text-primary transition-colors py-2 border-b border-white/[0.04]"
            >
              Security
            </a>
            <a
              href="https://github.com"
              target="_blank"
              rel="noreferrer"
              onClick={() => setIsMobileMenuOpen(false)}
              className="text-lg font-sans font-medium text-surface-dark-fg hover:text-primary transition-colors py-2 border-b border-white/[0.04]"
            >
              GitHub
            </a>
            <a
              href="http://localhost:8000/docs"
              target="_blank"
              rel="noreferrer"
              onClick={() => setIsMobileMenuOpen(false)}
              className="text-lg font-sans font-medium text-surface-dark-fg hover:text-primary transition-colors py-2 border-b border-white/[0.04]"
            >
              Docs
            </a>
          </div>

          <div className="flex flex-col gap-4 pt-8 border-t border-surface-dark-border">
            <Link
              href="/login"
              onClick={() => setIsMobileMenuOpen(false)}
              className="w-full py-3 text-center text-sm font-sans font-medium text-surface-dark-muted hover:text-surface-dark-fg rounded-lg border border-surface-dark-border-strong bg-surface-dark-panel"
            >
              Sign in
            </Link>
            <Link
              href="/login"
              onClick={() => setIsMobileMenuOpen(false)}
              className="w-full py-3 text-center text-sm font-mono uppercase tracking-wider font-bold text-white bg-primary hover:bg-primary-hover rounded-lg shadow-lg"
            >
              Connect GitHub →
            </Link>
          </div>
        </div>
      )}
    </>
  )
}
