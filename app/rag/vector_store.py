"""
Semantic RAG retrieval via pgvector — SEMANTIC CONTEXT RETRIEVAL ONLY.

This is intentionally the only place `similarity search` happens. Per the
PRD: "Vector search (RAG) is reserved for semantic context retrieval, not
fact-checking." The Critic's hallucination verification must NEVER call
into this module — it uses app/graph/verification/symbol_lookup.py
(exact AST/symbol match) instead.

Embedding model: sentence-transformers/all-MiniLM-L6-v2, run locally.
384-dim output — must match the vector(384) column in Supabase exactly,
or every insert/query against incident_embeddings fails outright.
"""
from functools import lru_cache

from sentence_transformers import SentenceTransformer

from app.database import get_supabase
from app.repositories.embeddings import EmbeddingsRepository


@lru_cache
def _get_model() -> SentenceTransformer:
    # Loaded once per process, not per call — model load (reading weights
    # from disk/cache) is the expensive part; encoding individual strings
    # afterward is fast.
    return SentenceTransformer("all-MiniLM-L6-v2")


class VectorStore:
    def __init__(self):
        self._db = get_supabase()
        self._embeddings = EmbeddingsRepository()

    async def embed(self, text: str) -> list[float]:
        model = _get_model()
        # sentence-transformers' encode() is synchronous/CPU-bound. Fine to
        # call directly here since inputs are short review-context strings,
        # not large documents — this isn't a network call to await on.
        vector = model.encode(text, normalize_embeddings=True)
        return vector.tolist()

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