"""
Unit tests for LedgerRepository's per-finding-pattern HITL outcome
tracking (record_hitl_outcome / get_consecutive_rejections) — the history
agent_3_critic._decide_hitl_severity reads to demote a repeatedly-rejected
pattern's severity.
"""
from unittest.mock import MagicMock

from app.repositories.ledger import LedgerRepository


class FakeInsertQuery:
    def __init__(self, table: "FakeOutcomesTable", row: dict):
        self._table = table
        self._row = row

    def execute(self):
        self._table.rows.append(self._row)
        result = MagicMock()
        result.data = [self._row]
        return result


class FakeSelectQuery:
    def __init__(self, rows: list[dict]):
        self._rows = rows

    def eq(self, col, val):
        self._rows = [r for r in self._rows if r.get(col) == val]
        return self

    def order(self, col, desc=False):
        self._rows = sorted(self._rows, key=lambda r: r[col], reverse=desc)
        return self

    def limit(self, n):
        self._rows = self._rows[:n]
        return self

    def execute(self):
        result = MagicMock()
        result.data = self._rows
        return result


class FakeOutcomesTable:
    def __init__(self):
        self.rows: list[dict] = []
        self._seq = 0

    def insert(self, row: dict):
        self._seq += 1
        row = {**row, "created_at": row.get("created_at", self._seq)}
        return FakeInsertQuery(self, row)

    def select(self, *_a, **_k):
        return FakeSelectQuery(list(self.rows))


class FakeDB:
    def __init__(self):
        self.outcomes = FakeOutcomesTable()

    def table(self, name):
        assert name == "hitl_finding_outcomes"
        return self.outcomes


def _ledger_with_fake_db() -> tuple[LedgerRepository, FakeDB]:
    ledger = LedgerRepository.__new__(LedgerRepository)  # skip __init__'s get_supabase()
    db = FakeDB()
    ledger._db = db
    return ledger, db


def test_record_hitl_outcome_writes_a_row():
    ledger, db = _ledger_with_fake_db()
    ledger.record_hitl_outcome(
        repo_full_name="acme/widgets", review_id="rev-1", pattern_key="agent_2a_struct:boundary:repositories->routes",
        outcome="rejected",
    )
    assert len(db.outcomes.rows) == 1
    assert db.outcomes.rows[0]["pattern_key"] == "agent_2a_struct:boundary:repositories->routes"
    assert db.outcomes.rows[0]["outcome"] == "rejected"


def test_no_history_means_zero_consecutive_rejections():
    ledger, _db = _ledger_with_fake_db()
    assert ledger.get_consecutive_rejections("some:pattern") == 0


def test_counts_consecutive_rejections_most_recent_first():
    ledger, db = _ledger_with_fake_db()
    for i, outcome in enumerate(["approved", "rejected", "rejected", "rejected"]):
        db.outcomes.rows.append(
            {"pattern_key": "p", "outcome": outcome, "created_at": i}
        )
    assert ledger.get_consecutive_rejections("p") == 3


def test_approval_anywhere_in_recent_history_resets_the_streak():
    # Rejected, rejected, then approved, then rejected once more (most
    # recent) -> streak is 1, not 3, since the approval breaks the run.
    ledger, db = _ledger_with_fake_db()
    for i, outcome in enumerate(["rejected", "rejected", "approved", "rejected"]):
        db.outcomes.rows.append(
            {"pattern_key": "p", "outcome": outcome, "created_at": i}
        )
    assert ledger.get_consecutive_rejections("p") == 1


def test_rejections_for_a_different_pattern_do_not_count():
    ledger, db = _ledger_with_fake_db()
    db.outcomes.rows.append({"pattern_key": "other", "outcome": "rejected", "created_at": 0})
    assert ledger.get_consecutive_rejections("p") == 0
