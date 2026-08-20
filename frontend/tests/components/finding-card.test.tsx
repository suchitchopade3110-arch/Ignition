import { describe, it, expect, vi } from "vitest"
import { render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { FindingCard } from "@/components/reviews/finding-card"
import { Finding } from "@/types"

const baseFinding: Finding = {
  id: "f-1",
  agentId: "agent_2c_security",
  severity: "high",
  file: "app/services/github_client.py",
  line: 42,
  description: "Webhook signature comparison uses a non-constant-time equality check",
  rule: "security/timing-safe-compare",
  recommendation: "Use hmac.compare_digest instead of ==.",
}

describe("FindingCard", () => {
  it("shows the description and file:line summary while collapsed", () => {
    render(<FindingCard finding={baseFinding} />)
    expect(screen.getByText(baseFinding.description)).toBeInTheDocument()
    expect(screen.getByText("app/services/github_client.py:42")).toBeInTheDocument()
    // Detail panel content isn't in the DOM until expanded.
    expect(screen.queryByText(baseFinding.rule)).not.toBeInTheDocument()
  })

  it("omits the line number when the finding has none", () => {
    render(<FindingCard finding={{ ...baseFinding, line: undefined }} />)
    expect(screen.getByText("app/services/github_client.py")).toBeInTheDocument()
  })

  it("expands to reveal rule and recommendation on click, and collapses again", async () => {
    const user = userEvent.setup()
    render(<FindingCard finding={baseFinding} />)

    await user.click(screen.getByLabelText("Expand finding"))
    expect(await screen.findByText(baseFinding.rule)).toBeInTheDocument()
    expect(screen.getByText(baseFinding.recommendation)).toBeInTheDocument()

    await user.click(screen.getByLabelText("Collapse finding"))
    // AnimatePresence removes the panel after its exit animation, not
    // synchronously on click, so wait for it to actually leave the DOM.
    await waitFor(() => expect(screen.queryByText(baseFinding.rule)).not.toBeInTheDocument())
  })

  it("does not render a suggested-fix block or copy button when there is no fix", async () => {
    const user = userEvent.setup()
    render(<FindingCard finding={baseFinding} />)
    await user.click(screen.getByLabelText("Expand finding"))
    expect(screen.queryByLabelText("Copy suggested fix to clipboard")).not.toBeInTheDocument()
  })

  describe("suggested fix copy button", () => {
    const findingWithFix: Finding = {
      ...baseFinding,
      suggestedFix: "```python\nhmac.compare_digest(a, b)\n```",
    }

    // testing-library/user-event's setup() installs its own
    // navigator.clipboard polyfill (jsdom's is getter-only), so the mock
    // has to be (re)installed after setup() runs, inside each test, or
    // user-event clobbers it.
    function stubClipboard() {
      Object.defineProperty(navigator, "clipboard", {
        value: { writeText: vi.fn().mockResolvedValue(undefined) },
        configurable: true,
      })
    }

    it("strips markdown code fences and copies the raw fix to the clipboard", async () => {
      const user = userEvent.setup()
      stubClipboard()
      render(<FindingCard finding={findingWithFix} />)
      await user.click(screen.getByLabelText("Expand finding"))

      await user.click(screen.getByLabelText("Copy suggested fix to clipboard"))

      expect(navigator.clipboard.writeText).toHaveBeenCalledWith("hmac.compare_digest(a, b)\n")
      expect(await screen.findByText("Copied")).toBeInTheDocument()
    })

    it("does not toggle the card's expanded state when the copy button is clicked", async () => {
      const user = userEvent.setup()
      stubClipboard()
      render(<FindingCard finding={findingWithFix} />)
      await user.click(screen.getByLabelText("Expand finding"))

      await user.click(screen.getByLabelText("Copy suggested fix to clipboard"))

      // Rule/recommendation content must still be visible — the copy
      // button's stopPropagation must prevent the header's onClick (which
      // toggles `expanded`) from also firing.
      expect(screen.getByText(findingWithFix.rule)).toBeInTheDocument()
    })
  })
})
