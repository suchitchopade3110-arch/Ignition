"""
Historical architecture ledger + baseline risk scores.

Split out of database.py so ledger reads/writes are mockable in tests
without touching the vector store or a live Supabase connection.
"""
from app.database import get_supabase


class LedgerRepository:
    TABLE = "architecture_ledger"
    # Per-finding-pattern HITL history — separate from TABLE (the whole-PR
    # ACS/baseline history) because a single review's approve/reject
    # decision touches multiple finding patterns, and severity demotion
    # (agent_3_critic._decide_hitl_severity) needs to look history up by
    # pattern, not by review.
    OUTCOMES_TABLE = "hitl_finding_outcomes"

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

    def record_hitl_outcome(self, repo_full_name: str, review_id: str, pattern_key: str, outcome: str) -> None:
        """
        Called from app/main.py's approve_hitl/reject_hitl for every
        distinct finding pattern present in that review — not just once
        per review — so get_consecutive_rejections can answer "has this
        specific pattern been rejected repeatedly" instead of only "was
        the last review that happened to contain it approved or rejected".
        """
        self._db.table(self.OUTCOMES_TABLE).insert(
            {
                "repo_full_name": repo_full_name,
                "review_id": review_id,
                "pattern_key": pattern_key,
                "outcome": outcome,
            }
        ).execute()

    def get_consecutive_rejections(self, pattern_key: str, limit: int = 20) -> int:
        """
        Counts "rejected" outcomes for this pattern, most-recent first,
        stopping at the first "approved" (or the `limit` cutoff). An
        approval anywhere in the recent history means a human still
        trusts this pattern, so it resets the streak rather than just
        counting total rejections ever — a pattern that was rejected 5
        times, approved once, then rejected once more is a streak of 1,
        not 6.
        """
        result = (
            self._db.table(self.OUTCOMES_TABLE)
            .select("outcome")
            .eq("pattern_key", pattern_key)
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        count = 0
        for row in result.data or []:
            if row["outcome"] != "rejected":
                break
            count += 1
        return count