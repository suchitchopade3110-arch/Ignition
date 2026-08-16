"use client"

import { useEffect, useRef, useState } from "react"
import * as d3 from "d3"
import type { Feature, FeatureCollection, Geometry, Position } from "geojson"
import { cn } from "@/lib/utils"

interface RotatingEarthProps {
  /** Upper bound on canvas width in px. Actual size is clamped to the parent element. */
  width?: number
  /** Upper bound on canvas height in px. Actual size is clamped to the parent element. */
  height?: number
  className?: string
}

type LandFeature = Feature<Geometry>
type LandFeatureCollection = FeatureCollection<Geometry>

export default function RotatingEarth({ width = 800, height = 600, className }: RotatingEarthProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return

    const context2d = canvas.getContext("2d")
    if (!context2d) return
    // Rebound to a name TS can prove non-null inside the closures below —
    // narrowing on `const` doesn't reliably cross nested function boundaries.
    const context = context2d

    let containerWidth = 0
    let containerHeight = 0
    let radius = 0

    const projection = d3.geoOrthographic().clipAngle(90)
    const path = d3.geoPath(projection, context)

    // Sized from the parent element, not the viewport — this canvas lives
    // inside a fixed-height flex column on the landing page, not full-bleed.
    const resize = () => {
      const parent = canvas.parentElement
      const parentWidth = parent?.clientWidth || width
      const parentHeight = parent?.clientHeight || height

      containerWidth = Math.min(width, parentWidth)
      containerHeight = Math.min(height, parentHeight)
      radius = Math.min(containerWidth, containerHeight) / 2.5

      const dpr = Math.min(window.devicePixelRatio || 1, 2)
      canvas.width = containerWidth * dpr
      canvas.height = containerHeight * dpr
      canvas.style.width = `${containerWidth}px`
      canvas.style.height = `${containerHeight}px`
      context.setTransform(dpr, 0, 0, dpr, 0, 0)

      projection.scale(radius).translate([containerWidth / 2, containerHeight / 2])
      render()
    }

    const pointInPolygon = (point: Position, polygon: Position[]): boolean => {
      const [x, y] = point
      let inside = false

      for (let i = 0, j = polygon.length - 1; i < polygon.length; j = i++) {
        const [xi, yi] = polygon[i]
        const [xj, yj] = polygon[j]

        if (yi > y !== yj > y && x < ((xj - xi) * (y - yi)) / (yj - yi) + xi) {
          inside = !inside
        }
      }

      return inside
    }

    const pointInFeature = (point: Position, feature: LandFeature): boolean => {
      const { geometry } = feature

      if (geometry.type === "Polygon") {
        const coordinates = geometry.coordinates
        if (!pointInPolygon(point, coordinates[0])) return false
        for (let i = 1; i < coordinates.length; i++) {
          if (pointInPolygon(point, coordinates[i])) return false // inside a hole
        }
        return true
      }

      if (geometry.type === "MultiPolygon") {
        for (const polygon of geometry.coordinates) {
          if (pointInPolygon(point, polygon[0])) {
            let inHole = false
            for (let i = 1; i < polygon.length; i++) {
              if (pointInPolygon(point, polygon[i])) {
                inHole = true
                break
              }
            }
            if (!inHole) return true
          }
        }
        return false
      }

      return false
    }

    const generateDotsInPolygon = (feature: LandFeature, dotSpacing = 16): [number, number][] => {
      const dots: [number, number][] = []
      const bounds = d3.geoBounds(feature)
      const [[minLng, minLat], [maxLng, maxLat]] = bounds
      const stepSize = dotSpacing * 0.08

      for (let lng = minLng; lng <= maxLng; lng += stepSize) {
        for (let lat = minLat; lat <= maxLat; lat += stepSize) {
          const point: Position = [lng, lat]
          if (pointInFeature(point, feature)) {
            dots.push([lng, lat])
          }
        }
      }

      return dots
    }

    interface DotData {
      lng: number
      lat: number
    }

    const allDots: DotData[] = []
    let landFeatures: LandFeatureCollection | null = null

    function render() {
      context.clearRect(0, 0, containerWidth, containerHeight)

      const currentScale = projection.scale()
      const scaleFactor = currentScale / radius

      // Globe body
      context.beginPath()
      context.arc(containerWidth / 2, containerHeight / 2, currentScale, 0, 2 * Math.PI)
      context.fillStyle = "#000000"
      context.fill()
      context.strokeStyle = "#ffffff"
      context.lineWidth = 2 * scaleFactor
      context.stroke()

      if (!landFeatures) return

      // Graticule
      const graticule = d3.geoGraticule()
      context.beginPath()
      path(graticule())
      context.strokeStyle = "#ffffff"
      context.lineWidth = 1 * scaleFactor
      context.globalAlpha = 0.25
      context.stroke()
      context.globalAlpha = 1

      // Land outlines
      context.beginPath()
      landFeatures.features.forEach((feature) => path(feature))
      context.strokeStyle = "#ffffff"
      context.lineWidth = 1 * scaleFactor
      context.stroke()

      // Halftone dots
      allDots.forEach((dot) => {
        const projected = projection([dot.lng, dot.lat])
        if (
          projected &&
          projected[0] >= 0 &&
          projected[0] <= containerWidth &&
          projected[1] >= 0 &&
          projected[1] <= containerHeight
        ) {
          context.beginPath()
          context.arc(projected[0], projected[1], 1.2 * scaleFactor, 0, 2 * Math.PI)
          context.fillStyle = "#999999"
          context.fill()
        }
      })
    }

    const controller = new AbortController()

    const loadWorldData = async () => {
      try {
        setIsLoading(true)
        const response = await fetch(
          "https://raw.githubusercontent.com/martynafford/natural-earth-geojson/refs/heads/master/110m/physical/ne_110m_land.json",
          { signal: controller.signal }
        )
        if (!response.ok) throw new Error("Failed to load land data")

        landFeatures = (await response.json()) as LandFeatureCollection

        landFeatures.features.forEach((feature) => {
          generateDotsInPolygon(feature, 16).forEach(([lng, lat]) => {
            allDots.push({ lng, lat })
          })
        })

        render()
        setIsLoading(false)
      } catch {
        if (controller.signal.aborted) return
        setError("Failed to load land map data")
        setIsLoading(false)
      }
    }

    // Rotation and interaction
    const rotation: [number, number, number] = [0, 0, 0]
    let autoRotate = true
    const rotationSpeed = 0.5
    const prefersReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches

    const rotate = () => {
      if (autoRotate && !prefersReducedMotion) {
        rotation[0] += rotationSpeed
        projection.rotate(rotation)
        render()
      }
    }

    const rotationTimer = d3.timer(rotate)

    const handleMouseDown = (event: MouseEvent) => {
      autoRotate = false
      const startX = event.clientX
      const startY = event.clientY
      const startRotation: [number, number, number] = [...rotation]

      const handleMouseMove = (moveEvent: MouseEvent) => {
        const sensitivity = 0.5
        const dx = moveEvent.clientX - startX
        const dy = moveEvent.clientY - startY

        rotation[0] = startRotation[0] + dx * sensitivity
        rotation[1] = Math.max(-90, Math.min(90, startRotation[1] - dy * sensitivity))

        projection.rotate(rotation)
        render()
      }

      const handleMouseUp = () => {
        document.removeEventListener("mousemove", handleMouseMove)
        document.removeEventListener("mouseup", handleMouseUp)
        window.setTimeout(() => {
          autoRotate = true
        }, 10)
      }

      document.addEventListener("mousemove", handleMouseMove)
      document.addEventListener("mouseup", handleMouseUp)
    }

    const handleWheel = (event: WheelEvent) => {
      event.preventDefault()
      const factor = event.deltaY > 0 ? 0.9 : 1.1
      const newRadius = Math.max(radius * 0.5, Math.min(radius * 3, projection.scale() * factor))
      projection.scale(newRadius)
      render()
    }

    canvas.addEventListener("mousedown", handleMouseDown)
    canvas.addEventListener("wheel", handleWheel, { passive: false })
    window.addEventListener("resize", resize)

    resize()
    loadWorldData()

    return () => {
      controller.abort()
      rotationTimer.stop()
      canvas.removeEventListener("mousedown", handleMouseDown)
      canvas.removeEventListener("wheel", handleWheel)
      window.removeEventListener("resize", resize)
    }
  }, [width, height])

  if (error) {
    return (
      <div className={cn("flex items-center justify-center bg-card rounded-2xl p-8", className)}>
        <div className="text-center">
          <p className="text-destructive font-semibold mb-2">Error loading Earth visualization</p>
          <p className="text-muted-foreground text-sm">{error}</p>
        </div>
      </div>
    )
  }

  return (
    <div className={cn("relative", className)}>
      <canvas
        ref={canvasRef}
        className="w-full h-full rounded-2xl bg-background"
        aria-label="Rotating wireframe globe"
      />
      {!isLoading && (
        <div className="absolute bottom-4 left-4 text-xs text-muted-foreground px-2 py-1 rounded-md bg-elevated/80">
          Drag to rotate · Scroll to zoom
        </div>
      )}
    </div>
  )
}
