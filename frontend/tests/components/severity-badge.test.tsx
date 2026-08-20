import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"
import { SeverityBadge } from "@/components/ui/severity-badge"
import { SeverityLevel } from "@/types"

describe("SeverityBadge", () => {
  const levels: SeverityLevel[] = ["none", "low", "medium", "high", "critical"]

  it.each(levels)("renders the correct label for %s severity", (level) => {
    render(<SeverityBadge level={level} />)
    const expectedLabel = level.charAt(0).toUpperCase() + level.slice(1)
    expect(screen.getByText(expectedLabel)).toBeInTheDocument()
  })

  it("falls back to the 'none' styling for an unrecognized level", () => {
    // Findings arriving from an unvetted agent output could carry a
    // severity string the frontend doesn't know about; the badge must not
    // crash or render blank in that case.
    render(<SeverityBadge level={"unknown" as SeverityLevel} />)
    expect(screen.getByText("None")).toBeInTheDocument()
  })

  it("merges an extra className onto the badge", () => {
    render(<SeverityBadge level="critical" className="extra-class" />)
    expect(screen.getByText("Critical").closest("span")).toHaveClass("extra-class")
  })
})
