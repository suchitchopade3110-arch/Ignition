import { describe, it, expect } from "vitest"
import { render } from "@testing-library/react"
import { MarkdownPreview } from "@/components/reviews/markdown-preview"

// Audit P1-4: the preview used dangerouslySetInnerHTML on model-written
// text, a stored-XSS sink. It now renders through react-markdown, which
// never turns raw HTML into elements.
describe("MarkdownPreview", () => {
  it("never renders raw HTML from the comment as elements", () => {
    const { container } = render(
      <MarkdownPreview content={'<img src=x onerror=alert(1)>\n\n* item <img src=y onerror=alert(2)>\n\n<script>alert(3)</script>'} />,
    )
    expect(container.querySelector("img")).toBeNull()
    expect(container.querySelector("script")).toBeNull()
    expect(container.querySelector("[onerror]")).toBeNull()
  })

  it("renders bold and italic as real elements", () => {
    const { container } = render(<MarkdownPreview content={"**Rule regression** and *careful* text"} />)
    expect(container.querySelector("strong")?.textContent).toBe("Rule regression")
    expect(container.querySelector("em")?.textContent).toBe("careful")
  })

  it("renders the Critic's comment structure (heading, list, inline code)", () => {
    const { container, getByText } = render(
      <MarkdownPreview content={"## Ignition Review — ACS: 92.0\n- `[HIGH]` src/a.ts: unguarded null"} />,
    )
    expect(getByText("Ignition Review — ACS: 92.0").tagName).toBe("H2")
    expect(container.querySelector("li code")?.textContent).toBe("[HIGH]")
  })

  it("drops a javascript: link target", () => {
    const { container } = render(<MarkdownPreview content={"[click](javascript:alert(1))"} />)
    const href = container.querySelector("a")?.getAttribute("href") ?? ""
    expect(href.startsWith("javascript:")).toBe(false)
  })

  it("renders nothing without content", () => {
    const { container } = render(<MarkdownPreview content={undefined} />)
    expect(container.innerHTML).toBe("")
  })
})
