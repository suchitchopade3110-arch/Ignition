"""
Unit tests for ReviewRepository.get_stats()'s week-over-week issues-found
trend (app/repositories/dashboard.py::_issues_found_trend).

A bare unittest.mock.MagicMock can't differentiate the six distinct query
shapes get_stats() issues against the same table (different .eq/.gte/.lt
filter combinations all sharing one .select/.execute chain), since Mock
call results don't vary by argument by default. FakeQuery below is a small
in-memory stand-in that actually applies the recorded filters to a fixed
row set, so each query in get_stats() gets the rows it would really match.
"""
from datetime import datetime, timedelta
from unittest.mock import MagicMock

from app.repositories.dashboard import ReviewRepository


class FakeQuery:
    def __init__(self, rows: list[dict]):
        self._rows = rows
        self._filters: list[tuple[str, str, object]] = []
        self._count_mode = None

    def select(self, *_args, **kwargs):
        self._count_mode = kwargs.get("count")
        return self

    def eq(self, col, val):
        self._filters.append(("eq", col, val))
        return self

    def gte(self, col, val):
        self._filters.append(("gte", col, val))
        return self

    def lt(self, col, val):
        self._filters.append(("lt", col, val))
        return self

    def order(self, *_a, **_k):
        return self

    def limit(self, *_a, **_k):
        return self

    def execute(self):
        rows = self._rows
        for op, col, val in self._filters:
            if op == "eq":
                rows = [r for r in rows if r.get(col) == val]
            elif op == "gte":
                # ISO8601 "...Z" timestamps compare correctly as strings.
                rows = [r for r in rows if str(r.get(col, "")) >= val]
            elif op == "lt":
                rows = [r for r in rows if str(r.get(col, "")) < val]

        result = MagicMock()
        result.data = rows
        result.count = len(rows) if self._count_mode == "exact" else None
        return result


class FakeDB:
    def __init__(self, rows: list[dict]):
        self._rows = rows

    def table(self, _name):
        return FakeQuery(self._rows)


def _iso(days_ago: float) -> str:
    return (datetime.utcnow() - timedelta(days=days_ago)).isoformat() + "Z"


def _repo_with_rows(rows: list[dict]) -> ReviewRepository:
    repo = ReviewRepository.__new__(ReviewRepository)  # skip __init__'s get_supabase()
    repo._db = FakeDB(rows)
    return repo


def test_issues_found_trend_none_without_prior_week_baseline():
    """No rows older than 7 days -> no baseline -> trend omitted, not a
    fabricated 0% or 100%."""
    rows = [
        {"created_at": _iso(1), "findings_count": 5, "status": "completed", "acs_score": 90},
    ]
    repo = _repo_with_rows(rows)
    stats = repo.get_stats()
    assert stats["issuesFoundTrend"] is None


def test_issues_found_trend_positive_when_recent_exceeds_prior():
    rows = [
        # prior week (7-14 days ago): 4 findings total
        {"created_at": _iso(10), "findings_count": 4, "status": "completed", "acs_score": 80},
        # recent week (0-7 days ago): 12 findings total -> +200%
        {"created_at": _iso(2), "findings_count": 12, "status": "completed", "acs_score": 85},
    ]
    repo = _repo_with_rows(rows)
    stats = repo.get_stats()
    trend = stats["issuesFoundTrend"]
    assert trend is not None
    assert trend["isPositive"] is True
    assert trend["value"] == 200.0


def test_issues_found_trend_negative_when_recent_below_prior():
    rows = [
        {"created_at": _iso(10), "findings_count": 20, "status": "completed", "acs_score": 80},
        {"created_at": _iso(2), "findings_count": 5, "status": "completed", "acs_score": 85},
    ]
    repo = _repo_with_rows(rows)
    stats = repo.get_stats()
    trend = stats["issuesFoundTrend"]
    assert trend is not None
    assert trend["isPositive"] is False
    assert trend["value"] == 75.0


def test_get_stats_shape_unaffected_by_trend_addition():
    """The four pre-existing fields keep working exactly as before."""
    rows = [
        {"created_at": _iso(1), "findings_count": 3, "status": "running", "acs_score": None},
        {"created_at": _iso(1), "findings_count": 2, "status": "waiting_hitl", "acs_score": None},
        {"created_at": _iso(1), "findings_count": 7, "status": "completed", "acs_score": 88},
    ]
    repo = _repo_with_rows(rows)
    stats = repo.get_stats()
    assert stats["activeReviews"] == 1
    assert stats["hitlPending"] == 1
    assert stats["avgAcsScore"] == 88.0
    assert stats["issuesFound"] == 12
    assert "issuesFoundTrend" in stats
