"""
Agent 2A — Structural Inspector (Sub-Graph A). Semantic (LLM).

Checks domain boundary violations, API contract breaks, architecture drift.
Runs in parallel with 2B and 2C — writes only to `findings`, which has a
list-concat reducer, so no collision with the other two.
"""
from pathlib import Path

from app.graph.state import ReviewState, Finding
from app.config import get_settings

PROMPT_PATH = Path(__file__).parent.parent.parent / "prompts" / "agent_2a_structural.md"


async def agent_2a_struct(state: ReviewState) -> dict:
    prompt_template = PROMPT_PATH.read_text()
    settings = get_settings()

    # TODO: wire up actual LLM call using settings.llm_provider / llm_model_name
    # response = await llm_client.complete(
    #     prompt_template.format(dependency_graph=state.ast_payload.dependency_graph)
    # )
    # findings = parse_structural_findings(response)

    findings: list[Finding] = []  # placeholder

    return {"findings": findings}