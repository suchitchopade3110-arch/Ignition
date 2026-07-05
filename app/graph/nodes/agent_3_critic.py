"""
Agent 3 — Critic & Synthesizer. Semantic (LLM) + deterministic verification.

Orchestration only. The two pieces of this that carry real design weight
are delegated out:
  - exact-lookup hallucination verification -> graph/verification/symbol_lookup.py
  - ACS + regression math                   -> graph/scoring.py

This keeps this file readable as "what happens", not "how the math/lookup
works" — and keeps those two pieces unit-testable in isolation.
"""
from pathlib import Path

from app.graph.state import ReviewState, Finding
from app.graph.verification.symbol_lookup import verify_symbol_exists, SymbolLookupError
from app.graph.scoring import compute_acs, is_rule_regression
from app.repositories.ledger import LedgerRepository

PROMPT_PATH = Path(__file__).parent.parent.parent / "prompts" / "agent_3_critic.md"


def _verify_findings(state: ReviewState) -> tuple[list[Finding], int]:
    """
    Exact AST/symbol verification of every finding before it's trusted.
    Returns (verified findings, count of hallucinated/dropped findings).
    """
    verified: list[Finding] = []
    hallucinated_count = 0

    for finding in state.findings:
        try:
            # Only checks findings that reference a specific symbol; findings
            # that don't (e.g. a general OSV hit) pass through unverified-but-trusted,
            # since they didn't make a codebase claim to begin with.
            if finding.description.startswith("symbol:"):
                verify_symbol_exists(state.ast_payload, finding.file_path, finding.description)
            verified.append(finding)
        except SymbolLookupError:
            hallucinated_count += 1

    return verified, hallucinated_count


def _decide_hitl_severity(verified_findings: list[Finding]) -> str:
    """Structured severity enum — the ONLY thing that drives the HITL gate."""
    severities = [f.severity for f in verified_findings]
    if "critical" in severities:
        return "critical"
    if "high" in severities:
        return "high"
    if "medium" in severities:
        return "medium"
    if "low" in severities:
        return "low"
    return "none"


async def agent_3_critic(state: ReviewState) -> dict:
    verified_findings, hallucinated_count = _verify_findings(state)

    total_deps = len(state.ast_payload.dependency_graph)
    total_violations = len(verified_findings)
    acs_score = compute_acs(total_deps, total_violations)

    ledger = LedgerRepository()
    baseline = ledger.get_baseline(state.repo_full_name)
    baseline_acs = baseline["acs_score"] if baseline else None
    regression = is_rule_regression(acs_score, baseline_acs)

    hitl_severity = _decide_hitl_severity(verified_findings)
    if regression and hitl_severity not in ("critical", "high"):
        hitl_severity = "high"  # regressions are never silently downgraded

    # Signal for routing.route_after_critic: None acs_score would mean
    # "verification incomplete" — here it's always set, so no retry is
    # triggered on this path. Retries are triggered instead when
    # hallucinated_count is high enough that findings can't be trusted yet.
    should_retry = hallucinated_count > 0 and state.hallucination_retry_count == 0

    return {
        "verified_findings": verified_findings,
        "acs_score": None if should_retry else acs_score,
        "is_regression": regression,
        "hitl_severity": hitl_severity,
        "hallucination_retry_count": 1 if should_retry else 0,
        "final_comment_markdown": _render_markdown(verified_findings, acs_score, regression),
    }


def _render_markdown(findings: list[Finding], acs_score: float, regression: bool) -> str:
    lines = [f"## Ignition Review — ACS: {acs_score:.1f}"]
    if regression:
        lines.append("**Rule regression detected against baseline.**")
    for f in findings:
        lines.append(f"- `[{f.severity.upper()}]` {f.file_path}: {f.description}")
    return "\n".join(lines) if findings else "No findings. Clean pass."