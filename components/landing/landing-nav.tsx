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

  return (
    <>
      <motion.header
        initial={{ y: -100 }}
        animate={{ y: 0 }}
        transition={{ type: "spring", stiffness: 300, damping: 30 }}
        className={`fixed top-0 left-0 right-0 z-50 transition-all duration-300 ${
          isScrolled 
            ? "bg-background/80 backdrop-blur-md border-b border-border shadow-sm py-3" 
            : "bg-transparent py-5"
        }`}
      >
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between">
            <Link href="/" className="flex items-center gap-3 group">
              <div className="relative h-9 w-9 flex items-center justify-center transition-transform group-hover:scale-105">
                <Image 
                  src="/logo.svg" 
                  alt="Ignition" 
                  fill
                  className="object-contain"
                  priority
                />
              </div>
              <span className="text-2xl font-bold tracking-tight text-foreground hidden sm:block">Ignition</span>
            </Link>

            <nav className="hidden md:flex items-center gap-8">
              <a href="#features" className="text-sm font-medium text-muted-foreground hover:text-foreground transition-colors">Features</a>
              <a href="#architecture" className="text-sm font-medium text-muted-foreground hover:text-foreground transition-colors">Architecture</a>
              <a href="#demo" className="text-sm font-medium text-muted-foreground hover:text-foreground transition-colors">Demo</a>
              <a href="#technology" className="text-sm font-medium text-muted-foreground hover:text-foreground transition-colors">Technology</a>
              <a href="#faq" className="text-sm font-medium text-muted-foreground hover:text-foreground transition-colors">FAQ</a>
            </nav>

            <div className="hidden md:flex items-center gap-4">
              <Link href="/login" className="text-sm font-medium text-muted-foreground hover:text-foreground transition-colors">
                Login
              </Link>
              <Link 
                href="/login"
                className="group flex items-center gap-2 px-5 py-2.5 bg-primary text-primary-foreground text-sm font-semibold rounded-full hover:bg-primary/90 transition-all shadow-[0_0_15px_rgba(255,69,0,0.3)] hover:shadow-[0_0_25px_rgba(255,69,0,0.5)]"
              >
                Get Started
                <ArrowRight className="w-4 h-4 transition-transform group-hover:translate-x-1" />
              </Link>
            </div>

            <button 
              className="md:hidden p-2 text-muted-foreground hover:text-foreground"
              onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
            >
              {isMobileMenuOpen ? <X className="h-6 w-6" /> : <Menu className="h-6 w-6" />}
            </button>
          </div>
        </div>
      </motion.header>

      {/* Mobile Menu Overlay */}
      {isMobileMenuOpen && (
        <div className="fixed inset-0 z-40 bg-background/95 backdrop-blur-sm md:hidden pt-24 px-4">
          <div className="flex flex-col gap-6 text-center">
            <a href="#features" onClick={() => setIsMobileMenuOpen(false)} className="text-xl font-medium text-foreground">Features</a>
            <a href="#architecture" onClick={() => setIsMobileMenuOpen(false)} className="text-xl font-medium text-foreground">Architecture</a>
            <a href="#demo" onClick={() => setIsMobileMenuOpen(false)} className="text-xl font-medium text-foreground">Demo</a>
            <a href="#technology" onClick={() => setIsMobileMenuOpen(false)} className="text-xl font-medium text-foreground">Technology</a>
            <a href="#faq" onClick={() => setIsMobileMenuOpen(false)} className="text-xl font-medium text-foreground">FAQ</a>
            <div className="h-px bg-border my-4 mx-8" />
            <Link href="/login" className="text-xl font-medium text-foreground">Login</Link>
            <Link 
              href="/login"
              className="mx-auto w-full max-w-[200px] flex justify-center items-center gap-2 px-5 py-3 bg-primary text-primary-foreground text-lg font-semibold rounded-full mt-4"
            >
              Get Started
            </Link>
          </div>
        </div>
      )}
    </>
  )
}
