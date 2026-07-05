"""
Architecture Compliance Score (ACS) + regression comparison against the
Supabase baseline. Isolated from agent_3_critic.py so the divide-by-zero
edge case (flagged in the PRD) is testable without the LLM/graph layer.
"""


def compute_acs(total_dependencies: int, total_violations: int) -> float:
    """
    ACS = (Total Dependencies - Total Violations) / Total Dependencies * 100

    Guards the PRD-flagged edge case: PRs/files with zero dependencies
    would otherwise divide by zero. Defined as a perfect score in that
    case — nothing to violate.
    """
    if total_dependencies == 0:
        return 100.0
    return (total_dependencies - total_violations) / total_dependencies * 100


def is_rule_regression(current_acs: float, baseline_acs: float | None, tolerance: float = 0.0) -> bool:
    """
    True if compliance dropped relative to the stored baseline.
    No baseline (first-ever PR for a repo) means nothing to regress against.
    """
    if baseline_acs is None:
        return False
    return current_acs < (baseline_acs - tolerance)