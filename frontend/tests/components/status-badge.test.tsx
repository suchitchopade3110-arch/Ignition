import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"
import { StatusBadge } from "@/components/ui/status-badge"
import { ReviewStatusType } from "@/types"

describe("StatusBadge", () => {
  const cases: Array<[ReviewStatusType, string]> = [
    ["queued", "Queued"],
    ["running", "Running"],
    ["paused", "Paused"],
    ["waiting_hitl", "Waiting HITL"],
    ["completed", "Completed"],
    ["failed", "Failed"],
    ["cancelled", "Cancelled"],
  ]

  it.each(cases)("renders the correct label for status %s", (status, label) => {
    render(<StatusBadge status={status} />)
    expect(screen.getByText(label)).toBeInTheDocument()
  })

  it("only pulses the icon while running", () => {
    const { rerender, container } = render(<StatusBadge status="running" />)
    expect(container.querySelector("svg")).toHaveClass("animate-pulse")

    rerender(<StatusBadge status="completed" />)
    expect(container.querySelector("svg")).not.toHaveClass("animate-pulse")
  })

  it("falls back to the 'queued' styling for an unrecognized status", () => {
    render(<StatusBadge status={"unknown" as ReviewStatusType} />)
    expect(screen.getByText("Queued")).toBeInTheDocument()
  })
})

// Audit P1-6: "posting" (an approval being posted) and "rejected" (dismissed
// by a maintainer) are real review statuses; the badge must name them
// instead of falling back to "Queued".
describe("StatusBadge — HITL resolution statuses", () => {
  it("labels the posting and rejected statuses", () => {
    render(<><StatusBadge status={"posting" as ReviewStatusType} /><StatusBadge status={"rejected" as ReviewStatusType} /></>)
    expect(screen.getByText("Posting")).toBeInTheDocument()
    expect(screen.getByText("Rejected")).toBeInTheDocument()
    expect(screen.queryByText("Queued")).not.toBeInTheDocument()
  })
})
