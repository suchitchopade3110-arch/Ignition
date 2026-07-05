"""
Agent 2A — Structural Inspector (Sub-Graph A). Semantic (LLM).

Checks domain boundary violations, API contract breaks, architecture drift.
Runs in parallel with 2B and 2C — writes only to `findings`, which has a
list-concat reducer, so no collision with the other two.
"""
import logging
from pathlib import Path

from app.graph.state import ReviewState, Finding
from app.services.llm_client import LLMClient
from app.services.finding_parser import parse_findings_json

logger = logging.getLogger(__name__)

PROMPT_PATH = Path(__file__).parent.parent.parent / "prompts" / "agent_2a_structural.md"


async def agent_2a_struct(state: ReviewState) -> dict:
    prompt_template = PROMPT_PATH.read_text()
    llm = LLMClient()

    dependency_graph_json = [edge.model_dump() for edge in state.ast_payload.dependency_graph]
    prompt = prompt_template.format(dependency_graph=dependency_graph_json)

    try:
        raw_response = await llm.complete(prompt)
        findings = parse_findings_json(raw_response, agent_name="agent_2a_struct")
    except Exception:
        # An LLM outage/error for this one agent shouldn't fail the whole
        # review — the other two sub-graphs and the Critic still run.
        logger.exception("agent_2a_struct LLM call failed; reporting no findings")
        findings: list[Finding] = []

    return {"findings": findings}