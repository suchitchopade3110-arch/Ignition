"use client"

import { useEffect, useRef } from "react"

interface Node3D {
  x: number
  y: number
  z: number
  lat: number
  lon: number
  radius: number
  color: string
  pulseSpeed: number
  pulseOffset: number
}

interface Arc3D {
  from: Node3D
  to: Node3D
  progress: number
  speed: number
}

export function TechnicalGlobe({ className = "" }: { className?: string }) {
  const canvasRef = useRef<HTMLCanvasElement>(null)

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return

    const ctx = canvas.getContext("2d")
    if (!ctx) return

    let animationFrameId: number
    let isVisible = true
    const prefersReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches

    // Resize handling
    let width = (canvas.width = canvas.parentElement?.clientWidth || 380)
    let height = (canvas.height = canvas.parentElement?.clientHeight || 380)
    let sphereRadius = Math.min(width, height) * 0.42

    const handleResize = () => {
      if (!canvas.parentElement) return
      width = canvas.width = canvas.parentElement.clientWidth || 380
      height = canvas.height = canvas.parentElement.clientHeight || 380
      sphereRadius = Math.min(width, height) * 0.42
    }
    window.addEventListener("resize", handleResize)

    // Visibility observer to pause animation when offscreen
    const observer = new IntersectionObserver(
      ([entry]) => {
        isVisible = entry.isIntersecting
      },
      { threshold: 0.1 }
    )
    observer.observe(canvas)

    let rotationY = 0
    const rotationX = 0.25 // slight tilt for 3D realism

    // Define Network Nodes on Globe
    const rawNodes: Array<{ lat: number; lon: number; color: string; r: number }> = [
      // Primary Hubs (Ignition Orange)
      { lat: 37.7749, lon: -122.4194, color: "#FF4D0A", r: 4 }, // SF
      { lat: 40.7128, lon: -74.006, color: "#FF4D0A", r: 3.5 }, // NYC
      { lat: 51.5074, lon: -0.1278, color: "#FF4D0A", r: 4 }, // London
      { lat: 35.6762, lon: 139.6503, color: "#FF4D0A", r: 3.5 }, // Tokyo
      { lat: 1.3521, lon: 103.8198, color: "#FF4D0A", r: 3.5 }, // Singapore
      { lat: 52.52, lon: 13.405, color: "#FF4D0A", r: 3 }, // Berlin
      { lat: -33.8688, lon: 151.2093, color: "#FF4D0A", r: 3 }, // Sydney
      { lat: 28.6139, lon: 77.209, color: "#FF4D0A", r: 3.5 }, // Delhi
      { lat: 48.8566, lon: 2.3522, color: "#FF4D0A", r: 3 }, // Paris
      { lat: 47.6062, lon: -122.3321, color: "#FF4D0A", r: 3 }, // Seattle
      { lat: 22.3193, lon: 114.1694, color: "#FF4D0A", r: 3 }, // Hong Kong
      { lat: 55.7558, lon: 37.6173, color: "#FF4D0A", r: 2.5 }, // Moscow
      { lat: -23.5505, lon: -46.6333, color: "#FF4D0A", r: 3 }, // Sao Paulo
      { lat: 31.2304, lon: 121.4737, color: "#FF4D0A", r: 3 }, // Shanghai

      // Secondary Network Nodes (Subtle White / Charcoal)
      { lat: 30.0444, lon: 31.2357, color: "#E4E4E7", r: 2 }, // Cairo
      { lat: -1.2921, lon: 36.8219, color: "#A1A1AA", r: 2 }, // Nairobi
      { lat: 19.4326, lon: -99.1332, color: "#E4E4E7", r: 2 }, // Mexico City
      { lat: 60.1699, lon: 24.9384, color: "#A1A1AA", r: 2 }, // Helsinki
      { lat: 59.3293, lon: 18.0686, color: "#E4E4E7", r: 2 }, // Stockholm
      { lat: 43.6532, lon: -79.3832, color: "#A1A1AA", r: 2 }, // Toronto
      { lat: 37.5665, lon: 126.978, color: "#E4E4E7", r: 2.5 }, // Seoul
      { lat: 12.9716, lon: 77.5946, color: "#E4E4E7", r: 2.5 }, // Bangalore
      { lat: 25.2048, lon: 55.2708, color: "#A1A1AA", r: 2 }, // Dubai
      { lat: -34.6037, lon: -58.3816, color: "#A1A1AA", r: 2 }, // Buenos Aires
      { lat: 41.0082, lon: 28.9784, color: "#E4E4E7", r: 2 }, // Istanbul
      { lat: 39.9042, lon: 116.4074, color: "#E4E4E7", r: 2 }, // Beijing
    ]

    const latLonTo3D = (lat: number, lon: number, r: number) => {
      const phi = ((90 - lat) * Math.PI) / 180
      const theta = ((lon + 180) * Math.PI) / 180
      return {
        x: -(r * Math.sin(phi) * Math.cos(theta)),
        y: r * Math.cos(phi),
        z: r * Math.sin(phi) * Math.sin(theta),
      }
    }

    const nodes: Node3D[] = rawNodes.map((n, i) => {
      const pos = latLonTo3D(n.lat, n.lon, sphereRadius)
      return {
        ...pos,
        lat: n.lat,
        lon: n.lon,
        radius: n.r,
        color: n.color,
        pulseSpeed: 0.03 + (i % 5) * 0.01,
        pulseOffset: (i * Math.PI) / 4,
      }
    })

    // Arcs between major hubs
    const arcs: Arc3D[] = [
      { from: nodes[0], to: nodes[1], progress: 0, speed: 0.008 }, // SF -> NYC
      { from: nodes[1], to: nodes[2], progress: 0.3, speed: 0.006 }, // NYC -> London
      { from: nodes[2], to: nodes[5], progress: 0.6, speed: 0.009 }, // London -> Berlin
      { from: nodes[2], to: nodes[3], progress: 0.1, speed: 0.005 }, // London -> Tokyo
      { from: nodes[3], to: nodes[4], progress: 0.5, speed: 0.007 }, // Tokyo -> Singapore
      { from: nodes[4], to: nodes[7], progress: 0.8, speed: 0.008 }, // Singapore -> Delhi
      { from: nodes[0], to: nodes[3], progress: 0.4, speed: 0.005 }, // SF -> Tokyo
      { from: nodes[7], to: nodes[2], progress: 0.2, speed: 0.006 }, // Delhi -> London
      { from: nodes[9], to: nodes[0], progress: 0.7, speed: 0.01 }, // Seattle -> SF
      { from: nodes[2], to: nodes[8], progress: 0.45, speed: 0.009 }, // London -> Paris
    ]

    let time = 0

    const render = () => {
      if (!isVisible) {
        animationFrameId = requestAnimationFrame(render)
        return
      }

      ctx.clearRect(0, 0, width, height)

      const cx = width / 2
      const cy = height / 2

      if (!prefersReducedMotion) {
        rotationY += 0.003 // slow, premium rotation
        time += 1
      }

      // Rotate and Project a point in 3D
      const project = (x: number, y: number, z: number) => {
        // Rotate around Y
        const cosY = Math.cos(rotationY)
        const sinY = Math.sin(rotationY)
        const x1 = x * cosY - z * sinY
        const z1 = z * cosY + x * sinY

        // Rotate around X
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

      // 1. Draw Globe Outer Glow & Atmospheric Rim
      const rimGradient = ctx.createRadialGradient(
        cx,
        cy,
        sphereRadius * 0.8,
        cx,
        cy,
        sphereRadius * 1.15
      )
      rimGradient.addColorStop(0, "rgba(255, 77, 10, 0)")
      rimGradient.addColorStop(0.85, "rgba(255, 77, 10, 0.06)")
      rimGradient.addColorStop(1, "rgba(255, 77, 10, 0)")

      ctx.fillStyle = rimGradient
      ctx.beginPath()
      ctx.arc(cx, cy, sphereRadius * 1.15, 0, Math.PI * 2)
      ctx.fill()

      // 2. Draw Sphere Base Disc
      const sphereDisc = ctx.createRadialGradient(
        cx - sphereRadius * 0.3,
        cy - sphereRadius * 0.3,
        sphereRadius * 0.1,
        cx,
        cy,
        sphereRadius
      )
      sphereDisc.addColorStop(0, "#191C1F")
      sphereDisc.addColorStop(0.7, "#121416")
      sphereDisc.addColorStop(1, "#090A0B")

      ctx.fillStyle = sphereDisc
      ctx.beginPath()
      ctx.arc(cx, cy, sphereRadius, 0, Math.PI * 2)
      ctx.fill()

      // Thin rim outline
      ctx.strokeStyle = "rgba(255, 255, 255, 0.08)"
      ctx.lineWidth = 1
      ctx.stroke()

      // 3. Draw Latitude Rings
      const latitudes = [-60, -40, -20, 0, 20, 40, 60]
      latitudes.forEach((lat) => {
        ctx.beginPath()
        let isFirst = true
        for (let lon = 0; lon <= 360; lon += 5) {
          const pt = latLonTo3D(lat, lon, sphereRadius)
          const proj = project(pt.x, pt.y, pt.z)

          // Only draw if on front or fade if on back
          if (proj.pz > -sphereRadius * 0.2) {
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
        ctx.strokeStyle = "rgba(255, 255, 255, 0.035)"
        ctx.lineWidth = 0.75
        ctx.stroke()
      })

      // 4. Draw Longitude Rings
      const longitudes = [0, 30, 60, 90, 120, 150, 180, 210, 240, 270, 300, 330]
      longitudes.forEach((lon) => {
        ctx.beginPath()
        let isFirst = true
        for (let lat = -80; lat <= 80; lat += 5) {
          const pt = latLonTo3D(lat, lon, sphereRadius)
          const proj = project(pt.x, pt.y, pt.z)

          if (proj.pz > -sphereRadius * 0.2) {
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
        ctx.strokeStyle = "rgba(255, 255, 255, 0.03)"
        ctx.lineWidth = 0.75
        ctx.stroke()
      })

      // 5. Draw Great-Circle Arcs and Travelling Pulse Signals
      arcs.forEach((arc) => {
        const fromPt = latLonTo3D(arc.from.lat, arc.from.lon, sphereRadius)
        const toPt = latLonTo3D(arc.to.lat, arc.to.lon, sphereRadius)

        const fromProj = project(fromPt.x, fromPt.y, fromPt.z)
        const toProj = project(toPt.x, toPt.y, toPt.z)

        // If at least one endpoint is visible
        if (fromProj.pz > -sphereRadius * 0.3 || toProj.pz > -sphereRadius * 0.3) {
          // Midpoint elevated in 3D to create orbital arc curve
          const midX = (fromPt.x + toPt.x) * 0.5 * 1.25
          const midY = (fromPt.y + toPt.y) * 0.5 * 1.25
          const midZ = (fromPt.z + toPt.z) * 0.5 * 1.25
          const midProj = project(midX, midY, midZ)

          // Draw Arc Line
          ctx.beginPath()
          ctx.moveTo(fromProj.px, fromProj.py)
          ctx.quadraticCurveTo(midProj.px, midProj.py, toProj.px, toProj.py)

          const arcAlpha = Math.max(
            0.05,
            Math.min(0.4, (fromProj.pz + toProj.pz + sphereRadius) / (sphereRadius * 2))
          )
          ctx.strokeStyle = `rgba(255, 77, 10, ${arcAlpha})`
          ctx.lineWidth = 1.2
          ctx.stroke()

          // Draw Traveling Signal Pulse on Arc
          if (!prefersReducedMotion) {
            arc.progress = (arc.progress + arc.speed) % 1
            const t = arc.progress
            // Quadratic Bezier interpolation in 2D
            const pulseX =
              (1 - t) * (1 - t) * fromProj.px + 2 * (1 - t) * t * midProj.px + t * t * toProj.px
            const pulseY =
              (1 - t) * (1 - t) * fromProj.py + 2 * (1 - t) * t * midProj.py + t * t * toProj.py

            ctx.beginPath()
            ctx.arc(pulseX, pulseY, 2.5, 0, Math.PI * 2)
            ctx.fillStyle = "#FF6A1A"
            ctx.shadowColor = "#FF4D0A"
            ctx.shadowBlur = 8
            ctx.fill()
            ctx.shadowBlur = 0
          }
        }
      })

      // 6. Draw Nodes (Depth Sorted)
      const projectedNodes = nodes.map((node) => {
        const pt = latLonTo3D(node.lat, node.lon, sphereRadius)
        const proj = project(pt.x, pt.y, pt.z)
        return {
          node,
          ...proj,
        }
      })

      // Sort back-to-front
      projectedNodes.sort((a, b) => a.pz - b.pz)

      projectedNodes.forEach((item) => {
        // Opacity based on z-depth
        const depthRatio = (item.pz + sphereRadius) / (sphereRadius * 2)
        if (depthRatio < 0.2) return // Back-face culled

        const alpha = Math.max(0.1, Math.min(1, depthRatio * 1.2))
        const pulse = prefersReducedMotion
          ? 1
          : 1 + Math.sin(time * item.node.pulseSpeed + item.node.pulseOffset) * 0.3
        const r = item.node.radius * pulse

        ctx.beginPath()
        ctx.arc(item.px, item.py, r, 0, Math.PI * 2)

        if (item.node.color === "#FF4D0A") {
          ctx.fillStyle = `rgba(255, 77, 10, ${alpha})`
          ctx.shadowColor = "rgba(255, 77, 10, 0.8)"
          ctx.shadowBlur = 6
          ctx.fill()
          ctx.shadowBlur = 0

          // Inner bright core
          ctx.beginPath()
          ctx.arc(item.px, item.py, r * 0.45, 0, Math.PI * 2)
          ctx.fillStyle = `rgba(255, 255, 255, ${alpha})`
          ctx.fill()
        } else {
          ctx.fillStyle = `rgba(228, 228, 231, ${alpha * 0.7})`
          ctx.fill()
        }
      })

      animationFrameId = requestAnimationFrame(render)
    }

    render()

    return () => {
      window.removeEventListener("resize", handleResize)
      observer.disconnect()
      cancelAnimationFrame(animationFrameId)
    }
  }, [])

  return (
    <div className={`relative flex items-center justify-center select-none ${className}`}>
      <canvas
        ref={canvasRef}
        className="w-full h-full max-w-[440px] max-h-[440px] object-contain pointer-events-none"
        aria-hidden="true"
      />
    </div>
  )
}
