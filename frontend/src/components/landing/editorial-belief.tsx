"use client"

import { motion } from "framer-motion"

export function EditorialBelief() {
  return (
    <section className="bg-[#F1EFE9] text-[#17191B] py-24 md:py-32 relative">
      <div className="max-w-7xl mx-auto px-6 sm:px-8 lg:px-12">
        {/* Orange Accent Dash */}
        <div className="h-1 w-10 bg-[#FF4D0A] mb-10" />

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-12 lg:gap-16 items-start">
          {/* Left: Oversized Statement */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5 }}
            className="lg:col-span-6"
          >
            <h2 className="text-3xl sm:text-4xl lg:text-5xl font-black tracking-tight text-[#17191B] uppercase leading-[1.05] font-sans">
              CODE REVIEW IS NOT <br />
              A CHECKBOX. <br />
              IT IS A CONTINUOUS <br />
              ENGINEERING SYSTEM.
            </h2>
          </motion.div>

          {/* Right: Editorial Explanation */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5, delay: 0.15 }}
            className="lg:col-span-6 flex flex-col gap-6 text-base sm:text-lg text-[#5F6265] leading-relaxed"
          >
            <p>
              Automated tools are noisy. Human reviewers are overwhelmed.
            </p>
            <p>
              Ignition combines AI agents, deep repository context, and deterministic validation to deliver reviews that are intelligent, consistent, and trusted.
            </p>
            <p className="text-[#FF4D0A] font-bold font-mono text-base pt-2">
              Built for engineers. By engineers.
            </p>
          </motion.div>
        </div>
      </div>
    </section>
  )
}
