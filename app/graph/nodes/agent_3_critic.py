"""
Agent 3 — Critic & Synthesizer. Semantic (LLM) + deterministic verification.

Orchestration only. The two pieces of this that carry real design weight
are delegated out:
  - exact-lookup hallucination verification -> graph/verification/symbol_lookup.py
  - ACS + regression math                   -> graph/scoring.py

The severity decision (_decide_hitl_severity) and the HITL gate it drives
are DELIBERATELY pure code, never LLM output — that's the whole point of
"deterministic escalation" from the PRD. The LLM is used only to write the
human-readable narrative on top of a verdict that's already been decided.
If that LLM call fails, the deterministic markdown rendering still works.

Every VERIFIED finding also gets recorded into the RAG store as a past
incident — this is what feeds Agent 2B's similar_incidents() lookup on
future PRs. Only verified findings are recorded (never raw/unverified
ones), so the incident corpus can't be poisoned by hallucinated claims
that were already filtered out earlier in this same function.
"""
import logging
from pathlib import Path

from app.graph.state import ReviewState, Finding, ResetFindings
from app.graph.verification.symbol_lookup import (
    verify_symbol_exists,
    verify_dependency_edge_or_raise,
    SymbolLookupError,
    DependencyEdgeLookupError,
)
from app.graph.scoring import compute_acs, is_rule_regression
from app.repositories.ledger import LedgerRepository
from app.rag.vector_store import VectorStore
from app.services.llm_client import get_llm_client
from app.config import get_settings

logger = logging.getLogger(__name__)

PROMPT_PATH = Path(__file__).parent.parent.parent / "prompts" / "agent_3_critic.md"


def _verify_findings(state: ReviewState) -> tuple[list[Finding], int]:
    """
    Exact AST/symbol verification of every finding before it's trusted.

    Only a finding that actually claims something checkable against the
    AST graph gets checked: `symbol_ref` (a specific declared symbol) or
    `dependency_edge_ref` (a specific cross-file import). A finding with
    neither — e.g. Agent 2C's security/supply-chain findings, which aren't
    claims about this repo's AST at all — passes through unverified by
    design; there's nothing in the AST graph to check it against.

    Returns (verified findings, count of hallucinated/dropped findings).
    """
    verified: list[Finding] = []
    hallucinated_count = 0

    for finding in state.findings:
        try:
            if finding.symbol_ref:
                verify_symbol_exists(state.ast_payload, finding.file_path, finding.symbol_ref)
            if finding.dependency_edge_ref:
                from_file, to_file = finding.dependency_edge_ref
                verify_dependency_edge_or_raise(state.ast_payload, from_file, to_file)
            verified.append(finding)
        except (SymbolLookupError, DependencyEdgeLookupError):
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


async def _generate_narrative(prompt_template: str, verified_findings: list[Finding]) -> str | None:
    """
    LLM-authored prose summary ONLY. Never touches severity, never touches
    the HITL decision — those are already final by the time this runs.
    Returns None on any failure so the caller falls back to plain rendering.
    """
    if not verified_findings:
        return None

    llm = get_llm_client()
    findings_json = [f.model_dump() for f in verified_findings]
    prompt = prompt_template.format(verified_findings=findings_json)

    try:
        return await llm.complete(prompt, json_mode=False, agent_name="agent_3_critic_narrative")
    except Exception:
        logger.exception("Critic narrative generation failed; falling back to plain rendering")
        return None


async def _record_incidents(repo_full_name: str, verified_findings: list[Finding]) -> None:
    """
    Records each verified finding as a past incident for future RAG
    retrieval by Agent 2B. Best-effort — a Supabase/embedding failure
    here must never fail the whole Critic node, since this is a
    forward-looking enrichment step, not part of the current review's
    correctness.
    """
    if not verified_findings:
        return

    vector_store = VectorStore()
    for finding in verified_findings:
        try:
            content = f"[{finding.agent}] {finding.file_path}: {finding.description}"
            await vector_store.record_incident(
                repo_full_name=repo_full_name,
                content=content,
                metadata={
                    "severity": finding.severity,
                    "file_path": finding.file_path,
                    "line": finding.line,
                    "agent": finding.agent,
                },
            )
        except Exception:
            logger.exception(
                "Failed to record incident for %s:%s — continuing with remaining findings",
                finding.file_path,
                finding.line,
            )


async def agent_3_critic(state: ReviewState) -> dict:
    verified_findings, hallucinated_count = _verify_findings(state)

    # ACS is denominated in dependency-graph edges, so only architecture
    # findings (Agent 2A — the only agent whose findings are claims about
    # those edges) count toward its numerator. Logic (2B) and security (2C)
    # findings are real, but they're not violations of *this* graph, and
    # mixing them in would score a PR against a denominator it has nothing
    # to do with (see scoring.py's docstring).
    total_deps = len(state.ast_payload.dependency_graph)
    total_violations = sum(1 for f in verified_findings if f.agent == "agent_2a_struct")
    acs_score = compute_acs(total_deps, total_violations)

    ledger = LedgerRepository()
    baseline = ledger.get_baseline(state.repo_full_name)
    baseline_acs = baseline["acs_score"] if baseline else None
    regression = is_rule_regression(acs_score, baseline_acs)

    hitl_severity = _decide_hitl_severity(verified_findings)
    if regression:
        hitl_severity = "critical"  # a regression always reaches a human, never silently auto-posted

    should_retry = hallucinated_count > 0 and state.hallucination_retry_count < get_settings().hallucination_retry_cap

    prompt_template = PROMPT_PATH.read_text()
    narrative = await _generate_narrative(prompt_template, verified_findings)

    # Record incidents only on a genuinely final pass — not on a retry
    # loop iteration, since should_retry means this run's findings haven't
    # been fully trusted yet and shouldn't be written into history early.
    if not should_retry:
        await _record_incidents(state.repo_full_name, verified_findings)

    result = {
        "verified_findings": verified_findings,
        "acs_score": acs_score,
        "is_regression": regression,
        "hitl_severity": hitl_severity,
        "critic_wants_retry": should_retry,
        "hallucination_retry_count": 1 if should_retry else 0,
        "final_comment_markdown": _render_markdown(verified_findings, acs_score, regression, narrative),
    }
    if should_retry:
        # ResetFindings, not `[]`: the retry edge (route_after_critic ->
        # agent_1_gate) re-runs the fan-out, and `findings` uses an
        # additive reducer everywhere else — an empty list would just
        # append zero items, leaving this pass's (partly hallucinated)
        # findings in place for the retry pass to pile on top of. This
        # sentinel tells the reducer to replace instead. Omitted entirely
        # on the non-retry path — returning state.findings here would
        # double it through that same additive reducer.
        result["findings"] = ResetFindings()
    return result


def _render_markdown(
    findings: list[Finding], acs_score: float, regression: bool, narrative: str | None
) -> str:
    lines = [f"## Ignition Review — ACS: {acs_score:.1f}"]
    if regression:
        lines.append("**Rule regression detected against baseline.**")
    if narrative:
        lines.append(narrative)
    for f in findings:
        lines.append(f"- `[{f.severity.upper()}]` {f.file_path}: {f.description}")
    return "\n".join(lines) if findings else "No findings. Clean pass."