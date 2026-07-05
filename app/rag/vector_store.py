"""
Semantic RAG retrieval via pgvector — SEMANTIC CONTEXT RETRIEVAL ONLY.

This is intentionally the only place `similarity search` happens. Per the
PRD: "Vector search (RAG) is reserved for semantic context retrieval, not
fact-checking." The Critic's hallucination verification must NEVER call
into this module — it uses app/graph/verification/symbol_lookup.py
(exact AST/symbol match) instead. Keeping them in separate files makes
that boundary a code-structure fact, not just a design intention.
"""
from app.database import get_supabase
from app.repositories.embeddings import EmbeddingsRepository


class VectorStore:
    def __init__(self):
        self._db = get_supabase()
        self._embeddings = EmbeddingsRepository()

    async def embed(self, text: str) -> list[float]:
        """Calls out to the configured embedding model. Stubbed pending model choice."""
        raise NotImplementedError("Wire up an embedding model call here")

    async def similar_incidents(
        self, repo_full_name: str, query_text: str, top_k: int = 5
    ) -> list[dict]:
        """
        Returns the top_k most semantically similar past incidents/decisions
        for Agent 2B to use as *context*, not as verified fact.
        """
        query_embedding = await self.embed(query_text)
        result = self._db.rpc(
            "match_incident_embeddings",
            {
                "query_embedding": query_embedding,
                "match_repo": repo_full_name,
                "match_count": top_k,
            },
        ).execute()
        return result.data or []

    async def record_incident(self, repo_full_name: str, content: str, metadata: dict) -> None:
        embedding = await self.embed(content)
        self._embeddings.insert(repo_full_name, content, embedding, metadata)