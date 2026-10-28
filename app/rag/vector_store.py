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
import asyncio
from functools import lru_cache
from typing import TYPE_CHECKING

from app.database import get_supabase
from app.repositories.embeddings import EmbeddingsRepository

if TYPE_CHECKING:  # pragma: no cover
    from sentence_transformers import SentenceTransformer

EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"


@lru_cache
def _get_model() -> "SentenceTransformer":
    # Loaded once per process, not per call — model load (reading weights
    # from disk/cache) is the expensive part; encoding individual strings
    # afterward is fast.
    #
    # Imported lazily (audit I-1): importing this module must not pull torch
    # into the FastAPI web process, which never embeds anything. Only the
    # Arq worker reaches this, on the first embed() call.
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(EMBEDDING_MODEL, device="cpu")


class VectorStore:
    def __init__(self):
        self._db = get_supabase()
        self._embeddings = EmbeddingsRepository()

    async def embed(self, text: str) -> list[float]:
        # encode() is synchronous and CPU-bound; run it off the event loop
        # (audit P1-7) so concurrent jobs and asyncio.wait_for keep working.
        def _encode() -> list[float]:
            return _get_model().encode(text, normalize_embeddings=True).tolist()

        return await asyncio.to_thread(_encode)

    async def similar_incidents(
        self, repo_full_name: str, query_text: str, top_k: int = 5
    ) -> list[dict]:
        """
        Returns the top_k most semantically similar past incidents/decisions
        for Agent 2B to use as *context*, not as verified fact.
        """
        query_embedding = await self.embed(query_text)
        # The Supabase client is synchronous: keep it off the event loop too.
        result = await asyncio.to_thread(
            lambda: self._db.rpc(
                "match_incident_embeddings",
                {
                    "query_embedding": query_embedding,
                    "match_repo": repo_full_name,
                    "match_count": top_k,
                },
            ).execute()
        )
        return result.data or []

    async def record_incident(self, repo_full_name: str, content: str, metadata: dict) -> None:
        embedding = await self.embed(content)
        await asyncio.to_thread(self._embeddings.insert, repo_full_name, content, embedding, metadata)