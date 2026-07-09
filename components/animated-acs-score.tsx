"use client"

import { useEffect, useState } from "react"


export function AnimatedAcsScore({ score }: { score: number }) {
  const [displayScore, setDisplayScore] = useState(0)

  useEffect(() => {
    let startTime: number
    const duration = 1000 // 1s
    const startScore = displayScore

    function animate(currentTime: number) {
      if (!startTime) startTime = currentTime
      const progress = Math.min((currentTime - startTime) / duration, 1)
      const easeOutQuart = 1 - Math.pow(1 - progress, 4)
      
      setDisplayScore(Math.round(startScore + (score - startScore) * easeOutQuart))
      
      if (progress < 1) {
        requestAnimationFrame(animate)
      }
    }
    
    requestAnimationFrame(animate)
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [score])

  let colorClass = "text-success"
  if (displayScore < 60) colorClass = "text-critical"
  else if (displayScore < 80) colorClass = "text-warning"
  else if (displayScore < 90) colorClass = "text-primary"

  return (
    <div className={`text-4xl font-bold tracking-tighter ${colorClass}`}>
      {displayScore}
    </div>
  )
}
