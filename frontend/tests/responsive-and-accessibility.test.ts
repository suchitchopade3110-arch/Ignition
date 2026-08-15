import { describe, it, expect } from "vitest"
import { formatAgentName } from "@/hooks/use-review-stream"

describe("Phase 3: Responsive & Accessibility Helpers", () => {
  describe("formatAgentName", () => {
    it("formats raw agent IDs into clean human-readable titles", () => {
      expect(formatAgentName("agent_1_triage")).toBe("Triage")
      expect(formatAgentName("agent_2a_struct")).toBe("Struct")
      expect(formatAgentName("agent_2b_chaos")).toBe("Chaos")
      expect(formatAgentName("agent_2c_security")).toBe("Security")
      expect(formatAgentName("agent_3_critic")).toBe("Critic")
    })

    it("handles arbitrary agent IDs gracefully", () => {
      expect(formatAgentName("custom_lint_checker")).toBe("Custom lint checker")
      expect(formatAgentName(undefined)).toBe("Analysis agent")
    })
  })

  describe("SSE Live Announcement Formatting", () => {
    it("generates human-readable announcements for critical events", () => {
      const agentCompletedMsg = `${formatAgentName("agent_2c_security")} analysis completed.`
      expect(agentCompletedMsg).toBe("Security analysis completed.")

      const acsUpdatedMsg = `Architecture Compliance Score updated to 92.`
      expect(acsUpdatedMsg).toBe("Architecture Compliance Score updated to 92.")

      const hitlWaitingMsg = "Review paused. Manual human approval required."
      expect(hitlWaitingMsg).toBe("Review paused. Manual human approval required.")

      const reviewCompletedMsg = "Autonomous code review completed."
      expect(reviewCompletedMsg).toBe("Autonomous code review completed.")
    })
  })
})
