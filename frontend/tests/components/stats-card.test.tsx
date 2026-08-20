import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"
import { Activity } from "lucide-react"
import { StatsCard } from "@/components/dashboard/stats-card"

describe("StatsCard", () => {
  it("renders title, value and description", () => {
    render(
      <StatsCard title="Active Reviews" value={12} description="Currently in flight" icon={Activity} />
    )
    expect(screen.getByText("Active Reviews")).toBeInTheDocument()
    expect(screen.getByText("12")).toBeInTheDocument()
    expect(screen.getByText("Currently in flight")).toBeInTheDocument()
  })

  it("renders a positive trend with a + sign and success styling", () => {
    render(
      <StatsCard
        title="Issues Found"
        value={4}
        icon={Activity}
        trend={{ value: 12, label: "vs last week", isPositive: true }}
      />
    )
    const trendValue = screen.getByText("+12%")
    expect(trendValue).toBeInTheDocument()
    expect(trendValue).toHaveClass("text-success")
    expect(screen.getByText("vs last week")).toBeInTheDocument()
  })

  it("renders a negative trend with a - sign and critical styling, using the absolute value", () => {
    render(
      <StatsCard
        title="Issues Found"
        value={4}
        icon={Activity}
        trend={{ value: -8, label: "vs last week", isPositive: false }}
      />
    )
    // trend.value is documented as always non-negative — the sign comes
    // from isPositive — but the component still guards with Math.abs so a
    // stray negative doesn't render a double minus.
    const trendValue = screen.getByText("-8%")
    expect(trendValue).toBeInTheDocument()
    expect(trendValue).toHaveClass("text-critical")
  })

  it("prefers the trend over the description when both are present", () => {
    render(
      <StatsCard
        title="Issues Found"
        value={4}
        description="fallback text"
        icon={Activity}
        trend={{ value: 5, label: "vs last week", isPositive: true }}
      />
    )
    expect(screen.queryByText("fallback text")).not.toBeInTheDocument()
    expect(screen.getByText("+5%")).toBeInTheDocument()
  })

  it("renders neither trend nor description block when both are absent", () => {
    const { container } = render(<StatsCard title="Active Reviews" value={0} icon={Activity} />)
    expect(container.querySelector(".mt-2")).not.toBeInTheDocument()
  })
})
