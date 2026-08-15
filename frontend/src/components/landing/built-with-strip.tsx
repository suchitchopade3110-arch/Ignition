"use client"

import { motion } from "framer-motion"

export function BuiltWithStrip() {
  return (
    <section className="py-20 md:py-24 relative bg-[#090A0B] border-t border-[#202326]">
      <div className="max-w-7xl mx-auto px-6 sm:px-8 lg:px-12">
        {/* Section Category Header */}
        <div className="mb-14">
          <span className="font-mono text-xs text-[#FF4D0A] uppercase tracking-widest font-bold">
            05 / BUILT WITH
          </span>
        </div>

        {/* Clean Monochrome Logos */}
        <motion.div
          initial={{ opacity: 0, y: 15 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5 }}
          className="flex flex-wrap items-center justify-between gap-8 md:gap-12 opacity-80"
        >
          {/* GitHub */}
          <div className="flex items-center gap-3 text-[#F4F3EF] hover:opacity-100 transition-opacity">
            <svg className="h-7 w-7 fill-current" viewBox="0 0 24 24">
              <path
                fillRule="evenodd"
                d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.531 1.032 1.531 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z"
                clipRule="evenodd"
              />
            </svg>
            <span className="text-xl font-bold tracking-tight">GitHub</span>
          </div>

          {/* FastAPI */}
          <div className="flex items-center gap-2.5 text-[#F4F3EF] hover:opacity-100 transition-opacity">
            <svg className="h-7 w-7 fill-current" viewBox="0 0 24 24">
              <path d="M12 2L3 13h7v9l9-11h-7L12 2z" />
            </svg>
            <span className="text-xl font-bold tracking-tight">FastAPI</span>
          </div>

          {/* Next.js */}
          <div className="flex items-center gap-2.5 text-[#F4F3EF] hover:opacity-100 transition-opacity">
            <svg className="h-7 w-7 fill-current" viewBox="0 0 24 24">
              <path d="M11.998 0C5.372 0 0 5.372 0 11.998c0 6.627 5.372 12.002 11.998 12.002 6.627 0 12.002-5.375 12.002-12.002C24 5.372 18.625 0 11.998 0zm6.812 17.37l-6.425-8.283v8.283H10.9V6.628h1.562l6.35 8.19V6.628h1.485v10.742h-.487z" />
            </svg>
            <span className="text-xl font-bold tracking-tight">Next.js</span>
          </div>

          {/* PostgreSQL */}
          <div className="flex items-center gap-2.5 text-[#F4F3EF] hover:opacity-100 transition-opacity">
            <svg className="h-7 w-7 fill-current" viewBox="0 0 24 24">
              <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 14.5h-2v-2h2v2zm0-4h-2V7h2v5.5z" />
            </svg>
            <span className="text-xl font-bold tracking-tight">PostgreSQL</span>
          </div>

          {/* OpenAI */}
          <div className="flex items-center gap-2.5 text-[#F4F3EF] hover:opacity-100 transition-opacity">
            <svg className="h-7 w-7 fill-current" viewBox="0 0 24 24">
              <path d="M22.28 9.42a5.55 5.55 0 0 0-.47-4.52 5.66 5.66 0 0 0-3.9-2.73 5.67 5.67 0 0 0-4.79.88 5.63 5.63 0 0 0-4.06-.55A5.64 5.64 0 0 0 5.3 4.86a5.68 5.68 0 0 0-.84 4.79 5.65 5.65 0 0 0-1.74 3.73 5.68 5.68 0 0 0 1.25 4.7 5.65 5.65 0 0 0 3.9 2.73 5.64 5.64 0 0 0 4.79-.88 5.65 5.65 0 0 0 4.06.55 5.64 5.64 0 0 0 3.76-2.36 5.68 5.68 0 0 0 .84-4.79 5.65 5.65 0 0 0 1.74-3.73 5.67 5.67 0 0 0-.78-4.14zM12 14.5a2.5 2.5 0 1 1 2.5-2.5 2.5 2.5 0 0 1-2.5 2.5z" />
            </svg>
            <span className="text-xl font-bold tracking-tight">OpenAI</span>
          </div>
        </motion.div>
      </div>
    </section>
  )
}
