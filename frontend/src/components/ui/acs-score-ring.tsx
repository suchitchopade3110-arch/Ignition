"use client"

import { motion, useReducedMotion } from "framer-motion"

interface AcsScoreRingProps {
  score: number // 0 to 100
  size?: number
  strokeWidth?: number
}

export function AcsScoreRing({ score, size = 64, strokeWidth = 4 }: AcsScoreRingProps) {
  const prefersReducedMotion = useReducedMotion()
  const radius = (size - strokeWidth) / 2
  const circumference = radius * 2 * Math.PI
  const offset = circumference - (score / 100) * circumference

  let color = "text-success"
  if (score < 60) color = "text-critical"
  else if (score < 80) color = "text-warning"
  else if (score < 90) color = "text-primary"

  return (
    <div className="relative flex items-center justify-center shrink-0" style={{ width: size, height: size }}>
      <svg className="transform -rotate-90" width={size} height={size}>
        {/* Background circle */}
        <circle
          className="text-border"
          strokeWidth={strokeWidth}
          stroke="currentColor"
          fill="transparent"
          r={radius}
          cx={size / 2}
          cy={size / 2}
        />
        {/* Foreground circle */}
        <motion.circle
          className={color}
          strokeWidth={strokeWidth}
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          strokeLinecap="round"
          stroke="currentColor"
          fill="transparent"
          r={radius}
          cx={size / 2}
          cy={size / 2}
          initial={prefersReducedMotion ? false : { strokeDashoffset: circumference }}
          animate={{ strokeDashoffset: offset }}
          transition={{ duration: 0.8, ease: "easeOut" }}
        />
      </svg>
      <div className="absolute flex flex-col items-center justify-center pointer-events-none select-none">
        <span className="text-xs font-bold text-foreground font-mono tabular-nums">{score}</span>
      </div>
    </div>
  )
}
