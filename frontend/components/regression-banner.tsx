import { AlertTriangle, TrendingDown } from "lucide-react"
import { RegressionAlert } from "@/lib/types"

interface RegressionBannerProps {
  regression: RegressionAlert
}

export function RegressionBanner({ regression }: RegressionBannerProps) {
  if (!regression.isRegression) return null

  return (
    <div className="rounded-xl border border-critical/30 bg-critical/10 p-5 shadow-sm">
      <div className="flex gap-4">
        <div className="flex-shrink-0 mt-0.5">
          <AlertTriangle className="h-5 w-5 text-critical" aria-hidden="true" />
        </div>
        <div className="flex-1">
          <h3 className="text-sm font-medium text-critical">
            Architecture Compliance Regression Detected
          </h3>
          <div className="mt-2 text-sm text-critical/80">
            <p>
              The Architecture Compliance Score has dropped from{" "}
              <strong className="font-bold">{regression.previousScore}</strong> to{" "}
              <strong className="font-bold">{regression.currentScore}</strong>.
            </p>
            {regression.ruleRegressed && (
              <p className="mt-1 font-medium">Violated Rule: {regression.ruleRegressed}</p>
            )}
            {regression.impact && (
              <p className="mt-2">
                <span className="font-semibold text-critical">Impact: </span>
                {regression.impact}
              </p>
            )}
            {regression.recommendation && (
              <p className="mt-2">
                <span className="font-semibold text-critical">Action Required: </span>
                {regression.recommendation}
              </p>
            )}
          </div>
        </div>
        <div className="flex-shrink-0 flex items-center justify-center bg-critical/20 h-12 w-12 rounded-full border border-critical/30">
          <TrendingDown className="h-6 w-6 text-critical" />
        </div>
      </div>
    </div>
  )
}
