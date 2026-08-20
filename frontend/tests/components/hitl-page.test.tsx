import { describe, it, expect, vi, beforeEach, afterEach } from "vitest"
import { render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { HitlItem } from "@/types"

// AppShell pulls in AuthGuard, the sidebar and the user menu — none of
// that is what this test is about, and standing it up would mean faking
// an authenticated session. Render children straight through instead.
vi.mock("@/components/layout/app-shell", () => ({
  AppShell: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
}))
vi.mock("@/components/layout/page-header", () => ({
  PageHeader: ({ title }: { title: string }) => <h1>{title}</h1>,
}))

const pushMock = vi.fn()
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: pushMock }),
}))

vi.mock("@/lib/api-client", () => ({
  apiClient: {
    getHitlPending: vi.fn(),
    approveHitl: vi.fn(),
    rejectHitl: vi.fn(),
  },
}))

// Imported after the mocks above so the module picks up the mocked apiClient.
const { apiClient } = await import("@/lib/api-client")
const { default: HitlPage } = await import("@/app/hitl/page")

const pendingItem: HitlItem = {
  id: "rev-1",
  repoId: "repo-1",
  repoName: "org/webapp",
  pullRequestNumber: 42,
  title: "Refactor auth middleware",
  status: "waiting_hitl",
  severity: "critical",
  findingsCount: 3,
  createdAt: new Date().toISOString(),
  author: "dev",
  branch: "feature/auth",
  commitSha: "abc123",
  filesChanged: 5,
  linesAdded: 80,
  linesDeleted: 12,
  acsScore: 62,
  previousAcsScore: 78,
  regression: { isRegression: true },
  agents: [],
  findings: [],
  diffs: [],
  waitingSince: new Date().toISOString(),
}

function renderPage() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  return render(
    <QueryClientProvider client={queryClient}>
      <HitlPage />
    </QueryClientProvider>
  )
}

describe("HitlPage approve/reject flow", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(apiClient.getHitlPending).mockResolvedValue([pendingItem])
    vi.mocked(apiClient.approveHitl).mockResolvedValue({ success: true })
    vi.mocked(apiClient.rejectHitl).mockResolvedValue({ success: true })
    vi.spyOn(window, "confirm").mockReturnValue(true)
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it("renders the pending item once loaded", async () => {
    renderPage()
    expect(await screen.findByText("Refactor auth middleware")).toBeInTheDocument()
  })

  it("shows the empty state once the queue clears", async () => {
    vi.mocked(apiClient.getHitlPending).mockResolvedValue([])
    renderPage()
    expect(await screen.findByText("All Caught Up!")).toBeInTheDocument()
  })

  it("confirms before calling approveHitl, then invokes it", async () => {
    const user = userEvent.setup()
    renderPage()
    await screen.findByText("Refactor auth middleware")

    await user.click(screen.getByRole("button", { name: /approve/i }))

    expect(window.confirm).toHaveBeenCalledWith(
      "Are you sure you want to approve this code review?"
    )
    await waitFor(() => expect(apiClient.approveHitl).toHaveBeenCalledWith("rev-1"))
    expect(apiClient.rejectHitl).not.toHaveBeenCalled()
  })

  it("confirms before calling rejectHitl, then invokes it", async () => {
    const user = userEvent.setup()
    renderPage()
    await screen.findByText("Refactor auth middleware")

    await user.click(screen.getByRole("button", { name: /reject/i }))

    expect(window.confirm).toHaveBeenCalledWith(
      "Are you sure you want to reject this code review?"
    )
    await waitFor(() => expect(apiClient.rejectHitl).toHaveBeenCalledWith("rev-1"))
    expect(apiClient.approveHitl).not.toHaveBeenCalled()
  })

  it("does not call the API when the confirmation dialog is dismissed", async () => {
    vi.spyOn(window, "confirm").mockReturnValue(false)
    const user = userEvent.setup()
    renderPage()
    await screen.findByText("Refactor auth middleware")

    await user.click(screen.getByRole("button", { name: /approve/i }))

    expect(apiClient.approveHitl).not.toHaveBeenCalled()
  })

  it("navigates to the review detail page from View Details", async () => {
    const user = userEvent.setup()
    renderPage()
    await screen.findByText("Refactor auth middleware")

    await user.click(screen.getByRole("button", { name: /view details/i }))

    expect(pushMock).toHaveBeenCalledWith("/reviews/rev-1")
  })
})
