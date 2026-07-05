"""
CRUD for stored embeddings (past incidents/decisions). Query-time similarity
search logic lives in app/rag/vector_store.py — this file only persists and
retrieves raw rows so the RAG layer isn't also responsible for schema/CRUD.
"""
from app.database import get_supabase


class EmbeddingsRepository:
    TABLE = "incident_embeddings"

    def __init__(self):
        self._db = get_supabase()

    def insert(self, repo_full_name: str, content: str, embedding: list[float], metadata: dict) -> None:
        self._db.table(self.TABLE).insert(
            {
                "repo_full_name": repo_full_name,
                "content": content,
                "embedding": embedding,
                "metadata": metadata,
            }
        ).execute()