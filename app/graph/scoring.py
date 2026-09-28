"""
Architecture Compliance Score (ACS) + regression comparison against the
Supabase baseline. Isolated from agent_3_critic.py so the divide-by-zero
edge case (flagged in the PRD) is testable without the LLM/graph layer.
"""
from app.schemas.ast_payload import DependencyEdge


def diff_scoped_dependency_count(dependency_graph: list[DependencyEdge], changed_files: list[str]) -> int:
    """
    Counts only the dependency-graph edges that originate from a file this
    PR actually changed, instead of the whole repo's edge count.

    A whole-repo denominator makes ACS numerically inert: a 3-edge diff
    landing a real violation in a 2,000-edge repo moves the score by a
    fraction of a point, so the number a reviewer sees never reflects what
    the PR itself did. Scoping to changed_files makes the score measure
    this diff, at the cost of being noisier PR-to-PR (see
    regression_tolerance in app/config.py, re-tuned for that noise).

    from_file (not to_file) is the scoping edge: an edge "belongs" to the
    diff when the file doing the importing is one this PR touched — that's
    the file whose import statements could actually have changed.
    """
    changed = set(changed_files)
    return sum(1 for edge in dependency_graph if edge.from_file in changed)


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