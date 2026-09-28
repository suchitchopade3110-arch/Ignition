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

from app.graph.state import ReviewState, Finding, ClearAgentFindings, RejectedClaim
from app.graph.verification.symbol_lookup import (
    verify_symbol_exists,
    verify_dependency_edge_or_raise,
    SymbolLookupError,
    DependencyEdgeLookupError,
)
from app.graph.verification.boundary_spec import BoundarySpec, find_layer, is_boundary_violation, load_default_boundary_spec
from app.graph.scoring import compute_acs, diff_scoped_dependency_count, is_rule_regression
from app.repositories.ledger import LedgerRepository
from app.rag.vector_store import VectorStore
from app.services.llm_client import get_llm_client
from app.config import get_settings

logger = logging.getLogger(__name__)

PROMPT_PATH = Path(__file__).parent.parent.parent / "prompts" / "agent_3_critic.md"

# Agents whose findings are claims about the repo's AST graph, and so must
# be able to name a checkable ref (symbol_ref or dependency_edge_ref) to be
# trusted at all — an architecture finding that names nothing checkable is
# treated the same as one that names something false: dropped as a
# hallucination, not passed through "unverified by design". That escape
# hatch is reserved for agents whose findings were never AST claims to
# begin with (Agent 2C's security/supply-chain findings, listed below).
MANDATORY_VERIFICATION_AGENTS = frozenset({"agent_2a_struct"})


class UnverifiableFindingError(Exception):
    """Raised when a mandatory-verification agent's finding names no checkable ref at all."""


def _verify_findings(state: ReviewState) -> tuple[list[Finding], list[Finding]]:
    """
    Exact AST/symbol verification of every finding before it's trusted.

    A finding that claims something checkable against the AST graph is
    checked against it: `symbol_ref` (a specific declared symbol) or
    `dependency_edge_ref` (a specific cross-file import). For
    MANDATORY_VERIFICATION_AGENTS, naming neither is ALSO treated as a
    hallucination — "verification is opt-in from the model's side" was a
    real gap: a vague architecture finding that never made a checkable
    claim used to sail through as "unverified by design" instead of being
    held to the same bar as a specific-but-wrong one. Other agents (2C's
    security/supply-chain findings) aren't claims about this repo's AST at
    all, so they keep passing through unverified — there's nothing in the
    AST graph to check them against, mandatory or not.

    Every finding that survives also gets a `verification_tier`. Passing
    hallucination verification only proves a finding's symbol/edge is real
    — it does NOT prove the finding's judgment ("this is a violation") is
    correct. Only a dependency_edge_ref that both verifies AND matches a
    disallowed boundary-spec rule (app/graph/verification/boundary_spec.py)
    is tagged `fact_checked`; everything else that survives (all 2B/2C
    findings, symbol_ref findings, and edge findings that are real but don't
    match any spec rule) is `contextual` — real, but not independently
    proven to be a genuine defect.

    Note: symbol_lookup.py's near-miss fallback means a claim that matches
    only after path normalization or barrel resolution is NOT hallucinated
    here — it's logged as a "near_miss_graph_gap" and passed straight
    through, so it never reaches the except block below at all.

    Returns (verified findings, dropped/hallucinated findings — the latter
    used by the caller to decide whether to retry and, if so, to build the
    rejected-claims list Agent 2A's re-prompt reads).
    """
    boundary_spec = load_default_boundary_spec()
    verified: list[Finding] = []
    hallucinated: list[Finding] = []

    for finding in state.findings:
        try:
            if not finding.symbol_ref and not finding.dependency_edge_ref:
                if finding.agent in MANDATORY_VERIFICATION_AGENTS:
                    raise UnverifiableFindingError(
                        f"{finding.agent} finding for {finding.file_path} names no "
                        f"symbol_ref/dependency_edge_ref — unverifiable, treated as a hallucination."
                    )
                finding.verification_tier = "contextual"
                finding.pattern_key = _finding_pattern_key(finding, boundary_spec)
                verified.append(finding)
                continue

            if finding.symbol_ref:
                verify_symbol_exists(state.ast_payload, finding.file_path, finding.symbol_ref)
            if finding.dependency_edge_ref:
                from_file, to_file = finding.dependency_edge_ref
                verify_dependency_edge_or_raise(state.ast_payload, from_file, to_file)
                finding.verification_tier = (
                    "fact_checked" if is_boundary_violation(boundary_spec, from_file, to_file) else "contextual"
                )
            else:
                finding.verification_tier = "contextual"
            finding.pattern_key = _finding_pattern_key(finding, boundary_spec)
            verified.append(finding)
        except (SymbolLookupError, DependencyEdgeLookupError, UnverifiableFindingError):
            hallucinated.append(finding)

    return verified, hallucinated


def _finding_pattern_key(finding: Finding, boundary_spec: BoundarySpec) -> str:
    """
    Deterministic identity for "the same shape of finding" across PRs, used
    to track HITL approve/reject outcomes per pattern instead of per
    review (see LedgerRepository.record_hitl_outcome).

    A dependency-edge finding whose edge falls between two spec-declared
    layers is keyed by that layer pair (e.g. "repositories->routes") —
    that's the actual reusable *rule* being violated, and it recurs across
    unrelated files/PRs the same way the boundary spec itself does. A
    symbol-ref finding is keyed by the specific symbol, since there's no
    layer-level rule to fall back to. Everything else (2B/2C findings, or
    an edge that matched no layer) falls back to agent+severity+description
    — coarser and less likely to recur verbatim, but still a fixed
    function of the finding, never randomized or LLM-decided.
    """
    if finding.dependency_edge_ref:
        from_file, to_file = finding.dependency_edge_ref
        from_layer = find_layer(boundary_spec, from_file)
        to_layer = find_layer(boundary_spec, to_file)
        if from_layer and to_layer:
            return f"{finding.agent}:boundary:{from_layer}->{to_layer}"
    if finding.symbol_ref:
        return f"{finding.agent}:symbol:{finding.file_path}:{finding.symbol_ref}"
    return f"{finding.agent}:{finding.severity}:{finding.description}"


SEVERITY_ORDER = ["none", "low", "medium", "high", "critical"]


def _demoted_severity(severity: str, consecutive_rejections: int, threshold: int) -> str:
    """
    One step down SEVERITY_ORDER once a pattern has been rejected by a
    human `threshold` times in a row, else unchanged. A single step, not
    scaled by how far past the threshold the streak is — this only needs
    to stop a stale pattern from paging at its original severity, not
    model how "very rejected" it is.
    """
    if consecutive_rejections < threshold:
        return severity
    idx = SEVERITY_ORDER.index(severity)
    return SEVERITY_ORDER[max(0, idx - 1)]


def _decide_hitl_severity(verified_findings: list[Finding], ledger: LedgerRepository) -> str:
    """
    Structured severity enum — the ONLY thing that drives the HITL gate.

    Still fully deterministic: for a fixed set of findings and a fixed
    ledger state, this always returns the same answer. The only thing
    "informed by history" is which severity each finding's pattern_key
    resolves to before the max-of-severities reduction below — a pattern
    with no rejection history (or fewer than hitl_demotion_threshold
    consecutive ones) is untouched.
    """
    threshold = get_settings().hitl_demotion_threshold
    severities = []
    for f in verified_findings:
        severity = f.severity
        if f.pattern_key:
            rejections = ledger.get_consecutive_rejections(f.pattern_key)
            severity = _demoted_severity(severity, rejections, threshold)
        severities.append(severity)
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

    Every verified finding is recorded — RAG is semantic *context* for 2B,
    not a fact store (see rag/vector_store.py's docstring), so a contextual
    finding is still useful recall even though it isn't hard-rule-proven.
    But it's tagged with its real tier and a distinct `source` so the
    incident corpus never lets a `contextual` (LLM-judgment) finding pass
    itself off as independently verified: only `fact_checked` findings are
    recorded under `source: "verified"`; everything else gets
    `source: "unverified_llm"`.
    """
    if not verified_findings:
        return

    vector_store = VectorStore()
    for finding in verified_findings:
        try:
            content = f"[{finding.agent}] {finding.file_path}: {finding.description}"
            source = "verified" if finding.verification_tier == "fact_checked" else "unverified_llm"
            await vector_store.record_incident(
                repo_full_name=repo_full_name,
                content=content,
                metadata={
                    "severity": finding.severity,
                    "file_path": finding.file_path,
                    "line": finding.line,
                    "agent": finding.agent,
                    "verification_tier": finding.verification_tier,
                    "source": source,
                },
            )
        except Exception:
            logger.exception(
                "Failed to record incident for %s:%s — continuing with remaining findings",
                finding.file_path,
                finding.line,
            )


async def agent_3_critic(state: ReviewState) -> dict:
    verified_findings, hallucinated_findings = _verify_findings(state)

    # ACS is denominated in dependency-graph edges, so only architecture
    # findings (Agent 2A — the only agent whose findings are claims about
    # those edges) count toward its numerator. Logic (2B) and security (2C)
    # findings are real, but they're not violations of *this* graph, and
    # mixing them in would score a PR against a denominator it has nothing
    # to do with (see scoring.py's docstring).
    #
    # Scoped to this PR's changed files, not the whole repo graph — see
    # diff_scoped_dependency_count's docstring for why a whole-repo
    # denominator makes the score numerically inert.
    total_deps = diff_scoped_dependency_count(state.ast_payload.dependency_graph, state.ast_payload.changed_files)
    total_violations = sum(1 for f in verified_findings if f.agent == "agent_2a_struct")
    acs_score = compute_acs(total_deps, total_violations)

    ledger = LedgerRepository()
    baseline = ledger.get_baseline(state.repo_full_name)
    baseline_acs = baseline["acs_score"] if baseline else None
    regression = is_rule_regression(
        acs_score, baseline_acs, tolerance=get_settings().regression_tolerance
    )

    hitl_severity = _decide_hitl_severity(verified_findings, ledger)
    if regression:
        hitl_severity = "critical"  # a regression always reaches a human, never silently auto-posted

    # Scoped to Agent 2A specifically: the retry edge (routing.py's
    # route_after_critic -> workflow.py's "retry_structural_recheck") only
    # re-invokes agent_2a_struct, not 2B/2C, so retrying is only worth
    # doing when 2A itself is what hallucinated. A stray hallucinated ref
    # from 2B/2C (neither is in MANDATORY_VERIFICATION_AGENTS, but either
    # could still optionally set one) is dropped below same as always —
    # it just can't trigger a retry that wouldn't fix it.
    hallucinated_2a = [f for f in hallucinated_findings if f.agent == "agent_2a_struct"]
    should_retry = bool(hallucinated_2a) and state.hallucination_retry_count < get_settings().hallucination_retry_cap

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
        # ClearAgentFindings("agent_2a_struct"), not `[]` and not a full
        # reset: the retry edge (route_after_critic -> agent_2a_struct
        # only, see workflow.py) re-runs just Agent 2A, and `findings`
        # uses an additive reducer everywhere else — an empty list would
        # just append zero items, leaving this pass's hallucinated 2A
        # findings in place for the retry to pile on top of. Scoping the
        # clear to agent_2a_struct (rather than wiping everything, the old
        # behavior) preserves 2B/2C's already-verified findings, since
        # they aren't being re-run this pass. Omitted entirely on the
        # non-retry path — returning state.findings here would double it
        # through that same additive reducer.
        result["findings"] = ClearAgentFindings(agent="agent_2a_struct")
        result["rejected_claims"] = [
            RejectedClaim(
                symbol_ref=f.symbol_ref,
                dependency_edge_ref=f.dependency_edge_ref,
                description=f.description,
            )
            for f in hallucinated_2a
        ]
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