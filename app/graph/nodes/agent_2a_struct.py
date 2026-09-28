"""
Agent 2A — Structural Inspector (Sub-Graph A). Semantic (LLM).

Checks domain boundary violations, API contract breaks, architecture drift.
Runs in parallel with 2B and 2C — writes only to `findings`, which has a
list-concat reducer, so no collision with the other two.
"""
import logging
from pathlib import Path

from app.graph.state import ReviewState, Finding
from app.services.llm_client import get_llm_client
from app.services.finding_parser import parse_findings_json

logger = logging.getLogger(__name__)

PROMPT_PATH = Path(__file__).parent.parent.parent / "prompts" / "agent_2a_structural.md"


def _format_rejected_claims(state: ReviewState) -> str:
    """
    Renders prior-pass hallucinated claims (state.rejected_claims, set by
    agent_3_critic on the narrow retry edge) into a block the prompt can
    show the model directly — empty string on a first pass, where there's
    nothing to warn about yet.
    """
    if not state.rejected_claims:
        return ""

    lines = [
        "The following claims from a previous pass did NOT verify against "
        "the real AST graph and were dropped as hallucinations. Do not repeat "
        "them, and do not guess a plausible-looking ref just to survive "
        "verification — omit symbol_ref/dependency_edge_ref entirely for a "
        "finding you can't ground precisely, rather than reaching for one of these again:",
    ]
    for claim in state.rejected_claims:
        if claim.symbol_ref:
            lines.append(f"- symbol_ref: \"{claim.symbol_ref}\" ({claim.description})")
        if claim.dependency_edge_ref:
            from_file, to_file = claim.dependency_edge_ref
            lines.append(f"- dependency_edge_ref: [\"{from_file}\", \"{to_file}\"] ({claim.description})")
    return "\n".join(lines)


async def agent_2a_struct(state: ReviewState) -> dict:
    prompt_template = PROMPT_PATH.read_text()
    llm = get_llm_client()

    dependency_graph_json = [edge.model_dump() for edge in state.ast_payload.dependency_graph]
    symbols_json = [symbol.model_dump() for symbol in state.ast_payload.symbols]
    prompt = prompt_template.format(
        dependency_graph=dependency_graph_json,
        symbols=symbols_json,
        diff=state.diff_text,
        rejected_claims=_format_rejected_claims(state),
    )

    try:
        raw_response = await llm.complete(prompt, agent_name="agent_2a_struct")
        findings = parse_findings_json(raw_response, agent_name="agent_2a_struct")
    except Exception:
        # An LLM outage/error for this one agent shouldn't fail the whole
        # review — the other two sub-graphs and the Critic still run.
        logger.exception("agent_2a_struct LLM call failed; reporting no findings")
        findings: list[Finding] = []

    return {"findings": findings}