"""
Historical architecture ledger + baseline risk scores.

Split out of database.py so ledger reads/writes are mockable in tests
without touching the vector store or a live Supabase connection.
"""
from app.database import get_supabase


class LedgerRepository:
    TABLE = "architecture_ledger"

    def __init__(self):
        self._db = get_supabase()

    def get_baseline(self, repo_full_name: str) -> dict | None:
        result = (
            self._db.table(self.TABLE)
            .select("*")
            .eq("repo_full_name", repo_full_name)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        return result.data[0] if result.data else None

    def write_baseline(self, repo_full_name: str, acs_score: float, risk_scores: dict) -> None:
        self._db.table(self.TABLE).insert(
            {
                "repo_full_name": repo_full_name,
                "acs_score": acs_score,
                "risk_scores": risk_scores,
            }
        ).execute()