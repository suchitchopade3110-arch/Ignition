"use client"

import { useEffect, useRef, useState } from "react"
import * as d3 from "d3"
import type { Feature, FeatureCollection, Geometry, LineString, Position } from "geojson"
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

// Brand orange, matching --color-primary / --color-primary-hover in
// globals.css. Canvas can't read CSS custom properties directly, so these
// mirror the tokens rather than referencing them.
const COLOR_PRIMARY = "#FF4500"
const COLOR_PRIMARY_HOVER = "#FF6A1A"
const COLOR_PRIMARY_SOFT = "#FF8A3D"
const COLOR_SIGNAL = "#FFD8B0"
const COLOR_BASE = "#09090B"

interface HubNode {
  lat: number
  lon: number
  isMajor: boolean
}

// A dozen engineering hubs with a handful of backbone connections between
// them — the same "network" reading as the canvas globe this replaced, but
// drawn as GeoJSON LineStrings so d3.geoPath handles the great-circle
// curvature and horizon clipping for free.
const HUBS: HubNode[] = [
  { lat: 37.77, lon: -122.42, isMajor: true }, // San Francisco
  { lat: 40.71, lon: -74.0, isMajor: true }, // New York
  { lat: 51.51, lon: -0.13, isMajor: true }, // London
  { lat: 12.97, lon: 77.59, isMajor: true }, // Bengaluru
  { lat: 35.68, lon: 139.65, isMajor: true }, // Tokyo
  { lat: -23.55, lon: -46.63, isMajor: true }, // Sao Paulo
  { lat: 52.52, lon: 13.41, isMajor: false }, // Berlin
  { lat: 1.35, lon: 103.82, isMajor: false }, // Singapore
  { lat: 25.2, lon: 55.27, isMajor: false }, // Dubai
  { lat: -33.87, lon: 151.21, isMajor: false }, // Sydney
]

const ARCS: [number, number][] = [
  [0, 1], // San Francisco <-> New York
  [1, 2], // New York <-> London
  [2, 6], // London <-> Berlin
  [2, 3], // London <-> Bengaluru
  [3, 7], // Bengaluru <-> Singapore
  [7, 4], // Singapore <-> Tokyo
  [4, 0], // Tokyo <-> San Francisco
  [1, 5], // New York <-> Sao Paulo
  [3, 8], // Bengaluru <-> Dubai
  [7, 9], // Singapore <-> Sydney
]

const ARC_FEATURES: Feature<LineString>[] = ARCS.map(([a, b]) => ({
  type: "Feature",
  properties: {},
  geometry: {
    type: "LineString",
    coordinates: [
      [HUBS[a].lon, HUBS[a].lat],
      [HUBS[b].lon, HUBS[b].lat],
    ],
  },
}))

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

    // Traveling signal: one bright pulse crosses a single arc at a time,
    // then hands off to the next. Mirrors the "sparse signal" behaviour of
    // the canvas globe this replaced. Only advances outside prefers-reduced-
    // motion — see the rotate() gate below.
    let activeArcIdx = 0
    let signalProgress = 0
    const signalSpeed = 0.006
    let signalCooldown = 0

    function render() {
      context.clearRect(0, 0, containerWidth, containerHeight)

      const currentScale = projection.scale()
      const scaleFactor = currentScale / radius

      // Globe body — near-black, matching the section background, so the
      // sphere reads as a wireframe floating on the page rather than a
      // filled disc.
      context.beginPath()
      context.arc(containerWidth / 2, containerHeight / 2, currentScale, 0, 2 * Math.PI)
      context.fillStyle = COLOR_BASE
      context.fill()
      context.strokeStyle = COLOR_PRIMARY
      context.globalAlpha = 0.5
      context.lineWidth = 2 * scaleFactor
      context.stroke()
      context.globalAlpha = 1

      if (!landFeatures) return

      // Graticule
      const graticule = d3.geoGraticule()
      context.beginPath()
      path(graticule())
      context.strokeStyle = COLOR_PRIMARY
      context.lineWidth = 1 * scaleFactor
      context.globalAlpha = 0.12
      context.stroke()
      context.globalAlpha = 1

      // Land outlines
      context.beginPath()
      landFeatures.features.forEach((feature) => path(feature))
      context.strokeStyle = COLOR_PRIMARY_HOVER
      context.lineWidth = 1 * scaleFactor
      context.globalAlpha = 0.45
      context.stroke()
      context.globalAlpha = 1

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
          context.fillStyle = COLOR_PRIMARY_SOFT
          context.globalAlpha = 0.3
          context.fill()
          context.globalAlpha = 1
        }
      })

      // Network arcs — great-circle LineStrings, clipped to the visible
      // hemisphere by the same projection.clipAngle(90) the land uses.
      context.beginPath()
      ARC_FEATURES.forEach((feature) => path(feature))
      context.strokeStyle = COLOR_PRIMARY
      context.lineWidth = 1.1 * scaleFactor
      context.globalAlpha = 0.55
      context.stroke()
      context.globalAlpha = 1

      // Point on the sphere currently facing the viewer — used below to test
      // whether a hub or the signal sits on the near or far hemisphere, the
      // same test projection.clipAngle(90) applies to paths internally.
      const facingPoint = projection.invert?.([containerWidth / 2, containerHeight / 2]) ?? [0, 0]

      // Hub nodes
      HUBS.forEach((hub) => {
        const projected = projection([hub.lon, hub.lat])
        if (!projected) return
        const [x, y] = projected
        const visible = d3.geoDistance([hub.lon, hub.lat], facingPoint) < Math.PI / 2
        if (!visible) return

        const nodeRadius = (hub.isMajor ? 3 : 2) * scaleFactor

        // Soft halo behind the node
        context.beginPath()
        context.arc(x, y, nodeRadius * 2.4, 0, 2 * Math.PI)
        context.fillStyle = COLOR_PRIMARY
        context.globalAlpha = hub.isMajor ? 0.16 : 0.08
        context.fill()
        context.globalAlpha = 1

        context.beginPath()
        context.arc(x, y, nodeRadius, 0, 2 * Math.PI)
        context.fillStyle = COLOR_PRIMARY
        context.fill()
      })

      // Traveling signal pulse along the active arc
      if (signalCooldown === 0) {
        const [fromIdx, toIdx] = ARCS[activeArcIdx]
        const from = HUBS[fromIdx]
        const to = HUBS[toIdx]
        const interpolate = d3.geoInterpolate([from.lon, from.lat], [to.lon, to.lat])
        const [lon, lat] = interpolate(signalProgress)
        const projected = projection([lon, lat])
        const visible = d3.geoDistance([lon, lat], facingPoint) < Math.PI / 2

        if (projected && visible) {
          context.beginPath()
          context.arc(projected[0], projected[1], 2.2 * scaleFactor, 0, 2 * Math.PI)
          context.fillStyle = COLOR_SIGNAL
          context.fill()
        }
      }
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

        if (signalCooldown > 0) {
          signalCooldown--
        } else {
          signalProgress += signalSpeed
          if (signalProgress >= 1) {
            signalProgress = 0
            activeArcIdx = (activeArcIdx + 1) % ARCS.length
            signalCooldown = 90 // brief pause between hops
          }
        }

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
