"use client"

import { useEffect, useRef } from "react"

interface HubNode {
  lat: number
  lon: number
  name: string
  radius: number
  isMajor: boolean
}

interface ConnectionArc {
  fromIdx: number
  toIdx: number
}

interface ActiveSignal {
  arcIdx: number
  progress: number
  speed: number
  active: boolean
}

export function NetworkGlobe({ className = "" }: { className?: string }) {
  const canvasRef = useRef<HTMLCanvasElement>(null)

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return

    const ctx = canvas.getContext("2d")
    if (!ctx) return

    let animationFrameId: number
    let isVisible = true
    const prefersReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches

    // High-DPI Canvas Sizing
    let displayWidth = 0
    let displayHeight = 0
    let dpr = Math.min(window.devicePixelRatio || 1, 2)

    const updateCanvasDimensions = () => {
      if (!canvas.parentElement) return
      displayWidth = canvas.parentElement.clientWidth || 480
      displayHeight = canvas.parentElement.clientHeight || 480
      dpr = Math.min(window.devicePixelRatio || 1, 2)

      canvas.width = displayWidth * dpr
      canvas.height = displayHeight * dpr
      canvas.style.width = `${displayWidth}px`
      canvas.style.height = `${displayHeight}px`
    }

    updateCanvasDimensions()
    window.addEventListener("resize", updateCanvasDimensions)

    // Visibility Observer
    const observer = new IntersectionObserver(
      ([entry]) => {
        isVisible = entry.isIntersecting
      },
      { threshold: 0.05 }
    )
    observer.observe(canvas)

    // 3D Spherical Conversion Helper
    const latLonToSphere = (lat: number, lon: number, radius: number) => {
      const phi = ((90 - lat) * Math.PI) / 180
      const theta = ((lon + 180) * Math.PI) / 180
      return {
        x: -(radius * Math.sin(phi) * Math.cos(theta)),
        y: radius * Math.cos(phi),
        z: radius * Math.sin(phi) * Math.sin(theta),
      }
    }

    // Generate 2,200+ Static Continental Landmass Points
    const landmassRegions = [
      { minLat: 15, maxLat: 65, minLon: -135, maxLon: -60, count: 420 }, // North America
      { minLat: -55, maxLat: 15, minLon: -80, maxLon: -35, count: 320 }, // South America
      { minLat: 36, maxLat: 68, minLon: -10, maxLon: 45, count: 380 }, // Europe
      { minLat: -35, maxLat: 36, minLon: -18, maxLon: 52, count: 380 }, // Africa
      { minLat: 15, maxLat: 55, minLon: 35, maxLon: 70, count: 220 }, // Middle East / Central Asia
      { minLat: 8, maxLat: 35, minLon: 68, maxLon: 92, count: 320 }, // India & South Asia
      { minLat: -10, maxLat: 55, minLon: 95, maxLon: 145, count: 440 }, // East & Southeast Asia
      { minLat: -45, maxLat: -10, minLon: 112, maxLon: 175, count: 200 }, // Australia / Oceania
    ]

    // Deterministic pseudo-random distribution
    let seed = 107
    const pseudoRandom = () => {
      seed = (seed * 9301 + 49297) % 233280
      return seed / 233280
    }

    const staticPoints: Array<{
      lat: number
      lon: number
      baseAlpha: number
      isOrange: boolean
      size: number
    }> = []

    landmassRegions.forEach((reg) => {
      for (let i = 0; i < reg.count; i++) {
        const lat = reg.minLat + pseudoRandom() * (reg.maxLat - reg.minLat)
        const lon = reg.minLon + pseudoRandom() * (reg.maxLon - reg.minLon)
        const isOrange = pseudoRandom() < 0.1
        const baseAlpha = 0.25 + pseudoRandom() * 0.45
        const size = 0.75 + pseudoRandom() * 0.95

        staticPoints.push({ lat, lon, baseAlpha, isOrange, size })
      }
    })

    // Fixed Major Intelligence Hubs & Secondary Nodes (Total ~20 nodes)
    const hubs: HubNode[] = [
      // Level 1: Major Global Hubs (6)
      { lat: 37.77, lon: -122.42, name: "San Francisco", radius: 4.4, isMajor: true },
      { lat: 40.71, lon: -74.0, name: "New York", radius: 4.2, isMajor: true },
      { lat: 51.51, lon: -0.13, name: "London", radius: 4.4, isMajor: true },
      { lat: 12.97, lon: 77.59, name: "Bengaluru", radius: 4.6, isMajor: true },
      { lat: 35.68, lon: 139.65, name: "Tokyo", radius: 4.4, isMajor: true },
      { lat: -23.55, lon: -46.63, name: "Sao Paulo", radius: 3.8, isMajor: true },

      // Level 2: Secondary Engineering Nodes (14)
      { lat: 47.6, lon: -122.33, name: "Seattle", radius: 2.2, isMajor: false },
      { lat: 30.27, lon: -97.74, name: "Austin", radius: 2.0, isMajor: false },
      { lat: 52.52, lon: 13.41, name: "Berlin", radius: 2.4, isMajor: false },
      { lat: 48.86, lon: 2.35, name: "Paris", radius: 2.0, isMajor: false },
      { lat: 59.33, lon: 18.07, name: "Stockholm", radius: 2.0, isMajor: false },
      { lat: 47.38, lon: 8.54, name: "Zurich", radius: 2.0, isMajor: false },
      { lat: 28.61, lon: 77.21, name: "New Delhi", radius: 2.5, isMajor: false },
      { lat: 19.08, lon: 72.88, name: "Mumbai", radius: 2.2, isMajor: false },
      { lat: 17.38, lon: 78.49, name: "Hyderabad", radius: 2.2, isMajor: false },
      { lat: 1.35, lon: 103.82, name: "Singapore", radius: 2.5, isMajor: false },
      { lat: 37.57, lon: 126.98, name: "Seoul", radius: 2.2, isMajor: false },
      { lat: -33.87, lon: 151.21, name: "Sydney", radius: 2.4, isMajor: false },
      { lat: -34.6, lon: -58.38, name: "Buenos Aires", radius: 2.0, isMajor: false },
      { lat: 25.2, lon: 55.27, name: "Dubai", radius: 2.4, isMajor: false },
    ]

    // Reduced to 9 Permanent Major Backbone Arcs (60-70% reduction)
    const connections: ConnectionArc[] = [
      { fromIdx: 0, toIdx: 1 }, // SF <-> NY
      { fromIdx: 1, toIdx: 2 }, // NY <-> London
      { fromIdx: 2, toIdx: 8 }, // London <-> Berlin
      { fromIdx: 2, toIdx: 3 }, // London <-> Bengaluru
      { fromIdx: 3, toIdx: 15 }, // Bengaluru <-> Singapore
      { fromIdx: 15, toIdx: 4 }, // Singapore <-> Tokyo
      { fromIdx: 4, toIdx: 0 }, // Tokyo <-> SF
      { fromIdx: 1, toIdx: 5 }, // NY <-> Sao Paulo
      { fromIdx: 3, toIdx: 19 }, // Bengaluru <-> Dubai
    ]

    // 2 Subtle Supporting Orbital Rings
    const orbitalRings = [
      {
        tiltX: 0.32,
        tiltY: 0.15,
        radiusMultiplier: 1.15,
        color: "rgba(255, 77, 10, 0.12)",
        speed: 0.0018,
        angle: 0.4,
        satellite: { angle: 0.4, size: 1.8, color: "#FF4D0A" },
      },
      {
        tiltX: -0.42,
        tiltY: 0.5,
        radiusMultiplier: 1.22,
        color: "rgba(244, 243, 239, 0.09)",
        speed: -0.0014,
        angle: 1.8,
        satellite: { angle: 2.6, size: 1.6, color: "#F4F3EF" },
      },
    ]

    // Animation Timing & State Management (No React state in loop)
    let rotationY = 0
    const rotationX = 0.2 // Fixed gentle orbital tilt

    // Organic Controlled Pulse: Only ONE major hub pulses every ~6 seconds
    let activePulsingHubIdx = 3 // Start with Bengaluru
    let pulsePhase = 0 // 0 to Math.PI

    // Sparse Signal: Only ONE packet active at a time
    const activeSignal: ActiveSignal = {
      arcIdx: 1, // NY -> London
      progress: 0,
      speed: 0.008, // ~3.5 seconds transit
      active: true,
    }
    let signalCooldown = 0

    // Main Render Loop
    const render = () => {
      if (!isVisible) {
        animationFrameId = requestAnimationFrame(render)
        return
      }

      ctx.save()
      ctx.scale(dpr, dpr)
      ctx.clearRect(0, 0, displayWidth, displayHeight)

      const cx = displayWidth / 2
      const cy = displayHeight / 2
      const globeRadius = Math.min(displayWidth, displayHeight) * 0.44

      if (!prefersReducedMotion) {
        // Calm, continuous 45-50 second rotation
        rotationY += 0.0016

        // Pulse progression
        pulsePhase += 0.02
        if (pulsePhase > Math.PI) {
          pulsePhase = 0
          // Pick next major hub (0, 1, 2, 3, 4, or 5)
          const majorHubIndices = [0, 1, 2, 3, 4, 5]
          const nextIndex = (majorHubIndices.indexOf(activePulsingHubIdx) + 1) % majorHubIndices.length
          activePulsingHubIdx = majorHubIndices[nextIndex]
        }

        // Sparse Signal progression
        if (activeSignal.active) {
          activeSignal.progress += activeSignal.speed
          if (activeSignal.progress >= 1) {
            activeSignal.active = false
            activeSignal.progress = 0
            signalCooldown = 180 + Math.floor(Math.random() * 120) // 3-5 seconds rest
          }
        } else if (signalCooldown > 0) {
          signalCooldown--
          if (signalCooldown === 0) {
            activeSignal.arcIdx = (activeSignal.arcIdx + 1) % connections.length
            activeSignal.active = true
            activeSignal.progress = 0
          }
        }

        // Orbit rings progression
        orbitalRings.forEach((ring) => {
          ring.angle += ring.speed
        })
      }

      // Rigid 3D Projection
      const project3D = (x: number, y: number, z: number) => {
        const cosY = Math.cos(rotationY)
        const sinY = Math.sin(rotationY)
        const x1 = x * cosY - z * sinY
        const z1 = z * cosY + x * sinY

        const cosX = Math.cos(rotationX)
        const sinX = Math.sin(rotationX)
        const y2 = y * cosX - z1 * sinX
        const z2 = z1 * cosX + y * sinX

        return {
          px: cx + x1,
          py: cy + y2,
          pz: z2,
        }
      }

      // 1. Subtle Volumetric Atmospheric Horizon Rim (Peak opacity <= 0.08)
      const atmosphereGradient = ctx.createRadialGradient(
        cx,
        cy,
        globeRadius * 0.85,
        cx,
        cy,
        globeRadius * 1.16
      )
      atmosphereGradient.addColorStop(0, "rgba(255, 77, 10, 0)")
      atmosphereGradient.addColorStop(0.85, "rgba(255, 77, 10, 0.04)")
      atmosphereGradient.addColorStop(0.96, "rgba(255, 77, 10, 0.07)")
      atmosphereGradient.addColorStop(1, "rgba(255, 77, 10, 0)")

      ctx.fillStyle = atmosphereGradient
      ctx.beginPath()
      ctx.arc(cx, cy, globeRadius * 1.16, 0, Math.PI * 2)
      ctx.fill()

      // 2. Near-Black Translucent Glass Sphere Body
      const sphereDisc = ctx.createRadialGradient(
        cx - globeRadius * 0.35,
        cy - globeRadius * 0.35,
        globeRadius * 0.1,
        cx,
        cy,
        globeRadius
      )
      sphereDisc.addColorStop(0, "rgba(20, 22, 25, 0.88)")
      sphereDisc.addColorStop(0.7, "rgba(14, 16, 18, 0.95)")
      sphereDisc.addColorStop(1, "rgba(9, 10, 11, 0.99)")

      ctx.fillStyle = sphereDisc
      ctx.beginPath()
      ctx.arc(cx, cy, globeRadius, 0, Math.PI * 2)
      ctx.fill()

      // Thin Specular Glass Edge
      ctx.strokeStyle = "rgba(255, 255, 255, 0.09)"
      ctx.lineWidth = 1
      ctx.stroke()

      // 3. Backside Orbital Rings (pz < 0)
      orbitalRings.forEach((ring) => {
        const ringRadius = globeRadius * ring.radiusMultiplier
        ctx.beginPath()
        let isFirst = true

        for (let a = 0; a <= Math.PI * 2; a += 0.08) {
          const rx = Math.cos(a) * ringRadius
          const ry = Math.sin(a) * ringRadius * Math.cos(ring.tiltX)
          const rz = Math.sin(a) * ringRadius * Math.sin(ring.tiltX)

          const cosY = Math.cos(ring.tiltY)
          const sinY = Math.sin(ring.tiltY)
          const rx1 = rx * cosY - rz * sinY
          const rz1 = rz * cosY + rx * sinY

          const proj = project3D(rx1, ry, rz1)

          if (proj.pz < 0) {
            if (isFirst) {
              ctx.moveTo(proj.px, proj.py)
              isFirst = false
            } else {
              ctx.lineTo(proj.px, proj.py)
            }
          } else {
            isFirst = true
          }
        }
        ctx.strokeStyle = ring.color.replace(/[\d.]+\)$/, "0.03)")
        ctx.lineWidth = 0.65
        ctx.stroke()
      })

      // 4. Project Dotted Landmass Points with Depth Occlusion
      staticPoints.forEach((pt) => {
        const spherePos = latLonToSphere(pt.lat, pt.lon, globeRadius)
        const proj = project3D(spherePos.x, spherePos.y, spherePos.z)

        // Depth perspective ratio: 0 (back) to 1 (front)
        const depthRatio = (proj.pz + globeRadius) / (globeRadius * 2)

        // Only draw points with visible opacity (heavy occlusion on back)
        if (depthRatio > 0.1) {
          const alpha = depthRatio > 0.5 ? pt.baseAlpha * depthRatio : pt.baseAlpha * 0.18 * depthRatio
          const size = pt.size * (0.7 + depthRatio * 0.45)

          ctx.beginPath()
          ctx.arc(proj.px, proj.py, size, 0, Math.PI * 2)

          if (pt.isOrange) {
            ctx.fillStyle = `rgba(255, 77, 10, ${alpha * 0.85})`
          } else {
            ctx.fillStyle = `rgba(244, 243, 239, ${alpha * 0.65})`
          }
          ctx.fill()
        }
      })

      // 5. Project Hub Nodes
      const projectedHubs = hubs.map((hub) => {
        const spherePos = latLonToSphere(hub.lat, hub.lon, globeRadius)
        const proj = project3D(spherePos.x, spherePos.y, spherePos.z)
        return {
          hub,
          ...proj,
        }
      })

      // 6. Draw 9 Major Geodesic Connection Arcs with Depth Separation
      connections.forEach((conn, idx) => {
        const fromHub = projectedHubs[conn.fromIdx]
        const toHub = projectedHubs[conn.toIdx]
        if (!fromHub || !toHub) return

        const fromPos = latLonToSphere(fromHub.hub.lat, fromHub.hub.lon, globeRadius)
        const toPos = latLonToSphere(toHub.hub.lat, toHub.hub.lon, globeRadius)

        const fromProj = project3D(fromPos.x, fromPos.y, fromPos.z)
        const toProj = project3D(toPos.x, toPos.y, toPos.z)

        // Only render if at least one endpoint is on front
        if (fromProj.pz > -globeRadius * 0.3 || toProj.pz > -globeRadius * 0.3) {
          // Elevated Midpoint for 3D great-circle arc
          const elev = 1.18
          const midX = (fromPos.x + toPos.x) * 0.5 * elev
          const midY = (fromPos.y + toPos.y) * 0.5 * elev
          const midZ = (fromPos.z + toPos.z) * 0.5 * elev
          const midProj = project3D(midX, midY, midZ)

          const arcDepth = (fromProj.pz + toProj.pz + globeRadius) / (globeRadius * 2)
          const isFront = arcDepth > 0.45

          const arcAlpha = isFront ? Math.min(0.42, arcDepth * 0.55) : Math.max(0.04, arcDepth * 0.12)

          // Draw Arc
          ctx.beginPath()
          ctx.moveTo(fromProj.px, fromProj.py)
          ctx.quadraticCurveTo(midProj.px, midProj.py, toProj.px, toProj.py)
          ctx.strokeStyle = `rgba(255, 77, 10, ${arcAlpha})`
          ctx.lineWidth = isFront ? 1.0 : 0.6
          ctx.stroke()

          // Draw Active Travelling Data Signal (Single packet at a time)
          if (!prefersReducedMotion && activeSignal.active && activeSignal.arcIdx === idx && isFront) {
            const t = activeSignal.progress

            // Quadratic Bezier interpolation in 2D
            const pulseX =
              (1 - t) * (1 - t) * fromProj.px + 2 * (1 - t) * t * midProj.px + t * t * toProj.px
            const pulseY =
              (1 - t) * (1 - t) * fromProj.py + 2 * (1 - t) * t * midProj.py + t * t * toProj.py

            // Luminous Signal Head
            ctx.beginPath()
            ctx.arc(pulseX, pulseY, 2.2, 0, Math.PI * 2)
            ctx.fillStyle = "#FFFFFF"
            ctx.shadowColor = "#FF4D0A"
            ctx.shadowBlur = 6
            ctx.fill()
            ctx.shadowBlur = 0

            // Tiny outer aura
            ctx.beginPath()
            ctx.arc(pulseX, pulseY, 4.2, 0, Math.PI * 2)
            ctx.fillStyle = "rgba(255, 77, 10, 0.35)"
            ctx.fill()
          }
        }
      })

      // 7. Draw Hub Nodes (Depth-Sorted)
      projectedHubs.sort((a, b) => a.pz - b.pz)

      projectedHubs.forEach((h, hubIdx) => {
        const depthRatio = (h.pz + globeRadius) / (globeRadius * 2)
        if (depthRatio < 0.15) return // Occluded on far back

        const alpha = Math.max(0.12, Math.min(1, depthRatio * 1.25))

        // Check if this hub is currently the single pulsing hub
        const isCurrentlyPulsing =
          !prefersReducedMotion && h.hub.isMajor && hubIdx === activePulsingHubIdx && depthRatio > 0.5
        const pulseScale = isCurrentlyPulsing ? 1 + Math.sin(pulsePhase) * 0.12 : 1
        const r = h.hub.radius * pulseScale * (0.7 + depthRatio * 0.45)

        // Subtle Halo only for Major Hubs
        if (h.hub.isMajor) {
          const haloRadius = isCurrentlyPulsing ? r * 2.8 : r * 2.0
          const glowGrad = ctx.createRadialGradient(h.px, h.py, r * 0.3, h.px, h.py, haloRadius)
          glowGrad.addColorStop(0, `rgba(255, 77, 10, ${alpha * 0.55})`)
          glowGrad.addColorStop(0.6, `rgba(255, 106, 26, ${alpha * 0.15})`)
          glowGrad.addColorStop(1, "rgba(255, 77, 10, 0)")

          ctx.fillStyle = glowGrad
          ctx.beginPath()
          ctx.arc(h.px, h.py, haloRadius, 0, Math.PI * 2)
          ctx.fill()

          // Tiny outer accent ring
          if (depthRatio > 0.5) {
            ctx.strokeStyle = `rgba(255, 160, 102, ${alpha * 0.35})`
            ctx.lineWidth = 0.75
            ctx.beginPath()
            ctx.arc(h.px, h.py, r * 1.6, 0, Math.PI * 2)
            ctx.stroke()
          }
        }

        // Hub Core
        ctx.beginPath()
        ctx.arc(h.px, h.py, r, 0, Math.PI * 2)
        if (h.hub.isMajor) {
          ctx.fillStyle = `rgba(255, 77, 10, ${alpha})`
          ctx.shadowColor = "#FF4D0A"
          ctx.shadowBlur = 4
          ctx.fill()
          ctx.shadowBlur = 0

          // White center point
          ctx.beginPath()
          ctx.arc(h.px, h.py, r * 0.35, 0, Math.PI * 2)
          ctx.fillStyle = `rgba(255, 255, 255, ${alpha})`
          ctx.fill()
        } else {
          ctx.fillStyle = `rgba(244, 243, 239, ${alpha * 0.75})`
          ctx.fill()
        }
      })

      // 8. Draw Frontside Orbital Rings & Single Satellite (pz >= 0)
      orbitalRings.forEach((ring) => {
        const ringRadius = globeRadius * ring.radiusMultiplier
        ctx.beginPath()
        let isFirst = true

        for (let a = 0; a <= Math.PI * 2; a += 0.05) {
          const rx = Math.cos(a) * ringRadius
          const ry = Math.sin(a) * ringRadius * Math.cos(ring.tiltX)
          const rz = Math.sin(a) * ringRadius * Math.sin(ring.tiltX)

          const cosY = Math.cos(ring.tiltY)
          const sinY = Math.sin(ring.tiltY)
          const rx1 = rx * cosY - rz * sinY
          const rz1 = rz * cosY + rx * sinY

          const proj = project3D(rx1, ry, rz1)

          if (proj.pz >= 0) {
            if (isFirst) {
              ctx.moveTo(proj.px, proj.py)
              isFirst = false
            } else {
              ctx.lineTo(proj.px, proj.py)
            }
          } else {
            isFirst = true
          }
        }
        ctx.strokeStyle = ring.color
        ctx.lineWidth = 0.75
        ctx.stroke()

        // Satellite on front
        const satAngle = (ring.angle + ring.satellite.angle) % (Math.PI * 2)
        const sx = Math.cos(satAngle) * ringRadius
        const sy = Math.sin(satAngle) * ringRadius * Math.cos(ring.tiltX)
        const sz = Math.sin(satAngle) * ringRadius * Math.sin(ring.tiltX)

        const cosY = Math.cos(ring.tiltY)
        const sinY = Math.sin(ring.tiltY)
        const sx1 = sx * cosY - sz * sinY
        const sz1 = sz * cosY + sx * sinY

        const sproj = project3D(sx1, sy, sz1)

        if (sproj.pz >= 0) {
          ctx.beginPath()
          ctx.arc(sproj.px, sproj.py, ring.satellite.size, 0, Math.PI * 2)
          ctx.fillStyle = ring.satellite.color
          ctx.fill()
        }
      })

      ctx.restore()
      animationFrameId = requestAnimationFrame(render)
    }

    render()

    return () => {
      window.removeEventListener("resize", updateCanvasDimensions)
      observer.disconnect()
      cancelAnimationFrame(animationFrameId)
    }
  }, [])

  return (
    <div className={`relative w-full h-full flex items-center justify-center select-none ${className}`}>
      <canvas
        ref={canvasRef}
        className="w-full h-full object-contain pointer-events-none"
        aria-hidden="true"
      />
    </div>
  )
}
