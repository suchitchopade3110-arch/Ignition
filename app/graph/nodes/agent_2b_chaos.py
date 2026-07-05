"""
Agent 2B — Chaos & Logic Assessor (Sub-Graph B). Semantic (LLM), verifies
against static analyzers.

Edge cases, error handling, N+1 query detection. This is the one agent
that legitimately uses semantic RAG (app/rag/vector_store.py) for context
on past incidents/decisions — that retrieval informs the LLM's reasoning,
it is NOT used to verify facts (that's the Critic's exact-lookup job).
"""
import json
import logging
from pathlib import Path

from app.graph.state import ReviewState, Finding
from app.rag.vector_store import VectorStore
from app.services.llm_client import LLMClient
from app.services.finding_parser import parse_findings_json

logger = logging.getLogger(__name__)

PROMPT_PATH = Path(__file__).parent.parent.parent / "prompts" / "agent_2b_chaos.md"


async def agent_2b_chaos(state: ReviewState) -> dict:
    prompt_template = PROMPT_PATH.read_text()
    vector_store = VectorStore()
    llm = LLMClient()

    # Semantic context only — informs reasoning, is not treated as verified fact.
    try:
        similar_incidents = await vector_store.similar_incidents(
            repo_full_name=state.repo_full_name,
            query_text="N+1 query patterns and edge-case handling in this diff",
        )
    except NotImplementedError:
        # Embedding model not yet wired up — proceed without historical
        # context rather than blocking this agent entirely.
        logger.warning("VectorStore.embed() not implemented; agent_2b running without RAG context")
        similar_incidents = []

    prompt = prompt_template.format(similar_incidents=json.dumps(similar_incidents))

    try:
        raw_response = await llm.complete(prompt)
        findings = parse_findings_json(raw_response, agent_name="agent_2b_chaos")
    except Exception:
        logger.exception("agent_2b_chaos LLM call failed; reporting no findings")
        findings: list[Finding] = []

    return {"findings": findings}