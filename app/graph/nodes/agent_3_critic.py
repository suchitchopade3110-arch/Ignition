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

from app.graph.state import ReviewState, Finding
from app.graph.verification.symbol_lookup import verify_symbol_exists, SymbolLookupError
from app.graph.scoring import compute_acs, is_rule_regression
from app.repositories.ledger import LedgerRepository
from app.rag.vector_store import VectorStore
from app.services.llm_client import LLMClient

logger = logging.getLogger(__name__)

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


async def _generate_narrative(prompt_template: str, verified_findings: list[Finding]) -> str | None:
    """
    LLM-authored prose summary ONLY. Never touches severity, never touches
    the HITL decision — those are already final by the time this runs.
    Returns None on any failure so the caller falls back to plain rendering.
    """
    if not verified_findings:
        return None

    llm = LLMClient()
    findings_json = [f.model_dump() for f in verified_findings]
    prompt = prompt_template.format(verified_findings=findings_json)

    try:
        return await llm.complete(prompt, json_mode=False)
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

    should_retry = hallucinated_count > 0 and state.hallucination_retry_count == 0

    prompt_template = PROMPT_PATH.read_text()
    narrative = await _generate_narrative(prompt_template, verified_findings)

    # Record incidents only on a genuinely final pass — not on a retry
    # loop iteration, since should_retry means this run's findings haven't
    # been fully trusted yet and shouldn't be written into history early.
    if not should_retry:
        await _record_incidents(state.repo_full_name, verified_findings)

    return {
        "verified_findings": verified_findings,
        "acs_score": None if should_retry else acs_score,
        "is_regression": regression,
        "hitl_severity": hitl_severity,
        "hallucination_retry_count": 1 if should_retry else 0,
        "final_comment_markdown": _render_markdown(verified_findings, acs_score, regression, narrative),
    }


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