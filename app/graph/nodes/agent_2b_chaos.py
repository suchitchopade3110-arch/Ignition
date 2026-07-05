"""
Agent 2B — Chaos & Logic Assessor (Sub-Graph B). Semantic (LLM), verifies
against static analyzers.

Edge cases, error handling, N+1 query detection. This is the one agent
that legitimately uses semantic RAG (app/rag/vector_store.py) for context
on past incidents/decisions — that retrieval informs the LLM's reasoning,
it is NOT used to verify facts (that's the Critic's exact-lookup job).
"""
from pathlib import Path

from app.graph.state import ReviewState, Finding
from app.rag.vector_store import VectorStore

PROMPT_PATH = Path(__file__).parent.parent.parent / "prompts" / "agent_2b_chaos.md"


async def agent_2b_chaos(state: ReviewState) -> dict:
    prompt_template = PROMPT_PATH.read_text()
    vector_store = VectorStore()

    # Semantic context only — informs reasoning, is not treated as verified fact.
    similar_incidents = await vector_store.similar_incidents(
        repo_full_name=state.repo_full_name,
        query_text="N+1 query patterns and edge-case handling in this diff",
    )

    # TODO: wire up LLM call with prompt_template + similar_incidents as context
    findings: list[Finding] = []  # placeholder

    return {"findings": findings}