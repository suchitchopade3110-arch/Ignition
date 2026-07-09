"use client"

import { useEffect, useState } from "react"
import { motion, useInView } from "framer-motion"
import { useRef } from "react"

function Counter({ from, to, duration, suffix = "", prefix = "" }: { from: number, to: number, duration: number, suffix?: string, prefix?: string }) {
  const [count, setCount] = useState(from)
  const ref = useRef(null)
  const inView = useInView(ref, { once: true, margin: "-100px" })

  useEffect(() => {
    if (inView) {
      let startTime: number
      let animationFrame: number

      const step = (timestamp: number) => {
        if (!startTime) startTime = timestamp
        const progress = Math.min((timestamp - startTime) / (duration * 1000), 1)
        
        // Easing function (easeOutQuart)
        const easeProgress = 1 - Math.pow(1 - progress, 4)
        setCount(Math.floor(easeProgress * (to - from) + from))

        if (progress < 1) {
          animationFrame = requestAnimationFrame(step)
        }
      }

      animationFrame = requestAnimationFrame(step)
      return () => cancelAnimationFrame(animationFrame)
    }
  }, [inView, from, to, duration])

  return (
    <span ref={ref} className="tabular-nums">
      {prefix}{count}{suffix}
    </span>
  )
}

export function MetricsSection() {
  return (
    <section className="py-20 relative z-10">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-8 lg:gap-12 divide-x divide-border/50">
          
          <motion.div 
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            className="flex flex-col items-center text-center px-4"
          >
            <h3 className="text-5xl font-bold text-foreground mb-2">
              <Counter from={0} to={4} duration={2} />
            </h3>
            <p className="text-sm font-medium text-muted-foreground uppercase tracking-wider">Parallel AI Agents</p>
          </motion.div>

          <motion.div 
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ delay: 0.1 }}
            className="flex flex-col items-center text-center px-4"
          >
            <h3 className="text-5xl font-bold text-foreground mb-2">
              <Counter from={0} to={100} duration={2.5} suffix="%" />
            </h3>
            <p className="text-sm font-medium text-muted-foreground uppercase tracking-wider">Deterministic Validation</p>
          </motion.div>

          <motion.div 
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ delay: 0.2 }}
            className="flex flex-col items-center text-center px-4"
          >
            <h3 className="text-5xl font-bold text-foreground mb-2">
              <Counter from={0} to={60} duration={2} prefix="<" suffix="s" />
            </h3>
            <p className="text-sm font-medium text-muted-foreground uppercase tracking-wider">Target Review Time</p>
          </motion.div>

          <motion.div 
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ delay: 0.3 }}
            className="flex flex-col items-center text-center px-4"
          >
            <h3 className="text-5xl font-bold text-foreground mb-2 text-transparent bg-clip-text bg-gradient-to-r from-primary to-orange-500">
              Ready
            </h3>
            <p className="text-sm font-medium text-muted-foreground uppercase tracking-wider">Enterprise Scale</p>
          </motion.div>

        </div>
      </div>
    </section>
  )
}
