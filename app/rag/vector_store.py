"""
Semantic RAG retrieval via pgvector — SEMANTIC CONTEXT RETRIEVAL ONLY.

This is intentionally the only place `similarity search` happens. Per the
PRD: "Vector search (RAG) is reserved for semantic context retrieval, not
fact-checking." The Critic's hallucination verification must NEVER call
into this module — it uses app/graph/verification/symbol_lookup.py
(exact AST/symbol match) instead.

Embedding model: sentence-transformers/all-MiniLM-L6-v2, run locally on
ONNX Runtime through fastembed (I-1: no torch, no CUDA wheels). 384-dim
output — must match the vector(384) column in Supabase exactly, or every
insert/query against incident_embeddings fails outright. The worker image
bakes the model in (FASTEMBED_CACHE_PATH, HF_HUB_OFFLINE=1).
"""
import asyncio
import math
import os
from functools import lru_cache
from typing import TYPE_CHECKING

from app.database import get_supabase
from app.repositories.embeddings import EmbeddingsRepository

if TYPE_CHECKING:  # pragma: no cover
    from fastembed import TextEmbedding

EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
EMBEDDING_DIM = 384
# Stored in each row's metadata, so scripts/reembed_incidents.py can tell
# rows written by this embedder from older ones.
EMBEDDER_ID = f"fastembed:{EMBEDDING_MODEL}"


@lru_cache
def _get_model() -> "TextEmbedding":
    # Loaded once per process, not per call — model load (reading weights
    # from disk/cache) is the expensive part; encoding individual strings
    # afterward is fast.
    #
    # Imported lazily (audit I-1): importing this module must not pull the
    # embedder into the FastAPI web process, which never embeds anything.
    # Only the Arq worker reaches this, on the first embed() call.
    from fastembed import TextEmbedding

    return TextEmbedding(model_name=EMBEDDING_MODEL, cache_dir=os.getenv("FASTEMBED_CACHE_PATH") or None)


def encode_texts(texts: list[str]) -> list[list[float]]:
    """Unit-length 384-dim vectors, one per text. Synchronous and CPU-bound:
    async callers run it in a thread (audit P1-7). A model that returns any
    other dimension is refused here, before the vector(384) column would."""
    vectors = []
    for raw in _get_model().embed(texts):
        vector = [float(x) for x in raw]
        if len(vector) != EMBEDDING_DIM:
            raise ValueError(f"embedder returned {len(vector)} dims, expected {EMBEDDING_DIM}")
        norm = math.sqrt(sum(x * x for x in vector)) or 1.0
        vectors.append([x / norm for x in vector])
    return vectors


class VectorStore:
    def __init__(self):
        self._db = get_supabase()
        self._embeddings = EmbeddingsRepository()

    async def embed(self, text: str) -> list[float]:
        # Encoding is synchronous and CPU-bound; run it off the event loop
        # (audit P1-7) so concurrent jobs and asyncio.wait_for keep working.
        [vector] = await asyncio.to_thread(encode_texts, [text])
        return vector

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
        metadata = {**metadata, "embedding_model": EMBEDDER_ID}
        await asyncio.to_thread(self._embeddings.insert, repo_full_name, content, embedding, metadata)