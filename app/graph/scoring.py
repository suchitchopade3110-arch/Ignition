"""
Architecture Compliance Score (ACS) + regression comparison against the
Supabase baseline. Isolated from agent_3_critic.py so the divide-by-zero
edge case (flagged in the PRD) is testable without the LLM/graph layer.
"""


def compute_acs(total_dependencies: int, total_violations: int) -> float:
    """
    ACS = (Total Dependencies - Total Violations) / Total Dependencies * 100

    Both inputs must be counted in the same unit — dependency-graph edges.
    Callers must pass `total_violations` as the count of *architecture*
    findings (Agent 2A) only: logic findings (2B) and security findings
    (2C) aren't claims about graph edges, so mixing them into this
    numerator would score a PR against a denominator it has nothing to do
    with. See agent_3_critic.py's call site.

    Guards the PRD-flagged edge case: PRs/files with zero dependencies
    would otherwise divide by zero. Defined as a perfect score in that
    case — nothing to violate.

    Clamped to [0, 100]: more architecture violations than dependency
    edges shouldn't be possible in practice, but the formula would
    otherwise go negative, and a negative "compliance score" is
    meaningless to compare against a baseline.
    """
    if total_dependencies == 0:
        return 100.0
    raw = (total_dependencies - total_violations) / total_dependencies * 100
    return max(0.0, min(100.0, raw))


def is_rule_regression(current_acs: float, baseline_acs: float | None, tolerance: float = 0.0) -> bool:
    """
    True if compliance dropped relative to the stored baseline.
    No baseline (first-ever PR for a repo) means nothing to regress against.
    """
    if baseline_acs is None:
        return False
    return current_acs < (baseline_acs - tolerance)