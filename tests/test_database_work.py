"""
I-10 (plus the P2 HNSW item): no indexes on reviews, stats computed in
Python over every row, one query per repo for the repo list, list
endpoints pulling every review's diff JSON, and nothing ever pruned. Now:
migrations_019 adds the two reviews indexes, a dashboard_stats(text[]) RPC
and a latest_review_per_repo(text[]) RPC (both with public execute
revoked), swaps the IVFFlat vector index for HNSW, and adds
prune_review_diffs(int); the repositories call the RPCs and select only
the columns they use; a daily Arq cron prunes diffs older than 30 days.
"""
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from app.repositories.dashboard import RepoRepository, ReviewRepository
from tests.fake_supabase import FakeSupabase

REPO_ROOT = Path(__file__).resolve().parents[1]


def _sql(number: int) -> str:
    [path] = REPO_ROOT.glob(f"migrations_{number:03d}_*.sql")
    return re.sub(r"\s+", " ", path.read_text())


def _iso(days_ago=0):
    return (datetime.now(timezone.utc) - timedelta(days=days_ago)).isoformat()


def _review(rid, repo, status, acs=None, findings=0, days_ago=0):
    return {"id": rid, "repo_full_name": repo, "pr_number": 1, "title": rid, "author": "a", "branch": "b",
            "commit_sha": rid, "status": status, "severity": "none", "acs_score": acs, "findings_count": findings,
            "created_at": _iso(days_ago), "diff_text": "+huge diff", "diffs": [{"file": "x"}],
            "verified_findings": [], "findings": [], "agents": [], "regression": None}


@pytest.fixture
def db():
    return FakeSupabase({
        "repositories": [{"id": f"acme_r{i}", "owner": "acme", "name": f"r{i}", "language": "TypeScript",
                          "installed": True} for i in range(3)],
        "reviews": [
            _review("a", "acme/r0", "completed", acs=90.0, findings=2, days_ago=40),
            _review("b", "acme/r0", "running", findings=1),
            _review("c", "acme/r1", "waiting_hitl", findings=3, days_ago=2),
            _review("d", "acme/r1", "completed", acs=70.0, days_ago=1),
            _review("e", "other/x", "completed", acs=10.0, findings=99),
        ],
    })


def _repos(db, cls):
    repo = cls.__new__(cls)
    repo._db = db
    return repo


def test_migration_adds_indexes_rpcs_hnsw_and_pruning():
    sql = _sql(19)
    assert "CREATE INDEX IF NOT EXISTS reviews_status_created_idx ON reviews (status, created_at DESC);" in sql
    assert "CREATE INDEX IF NOT EXISTS reviews_repo_created_idx ON reviews (repo_full_name, created_at DESC);" in sql
    assert "CREATE OR REPLACE FUNCTION dashboard_stats(repo_names text[]) RETURNS json LANGUAGE sql STABLE" in sql
    assert "SELECT DISTINCT ON (r.repo_full_name)" in sql
    assert "USING hnsw (embedding vector_cosine_ops)" in sql and "DROP INDEX IF EXISTS incident_embeddings_vector_idx;" in sql
    for fn in ("dashboard_stats(text[])", "latest_review_per_repo(text[])", "prune_review_diffs(int)"):
        assert f"REVOKE EXECUTE ON FUNCTION {fn} FROM anon, authenticated, public;" in sql


def test_stats_come_from_one_rpc(db):
    stats = _repos(db, ReviewRepository).get_stats(repo_names=frozenset({"acme/r0", "acme/r1"}))
    assert {k: stats[k] for k in ("activeReviews", "hitlPending", "avgAcsScore", "issuesFound")} == {
        "activeReviews": 1, "hitlPending": 1, "avgAcsScore": 80.0, "issuesFound": 6}
    assert [q for q in db.queries if q[0] == "rpc"] == [("rpc", "dashboard_stats", (("repo_names", ["acme/r0", "acme/r1"]),))]
    # Only the week-over-week trend still reads rows, and only findings_count.
    assert {cols for table, cols in db.selects if table == "reviews"} <= {"findings_count"}


def test_repo_list_is_one_rpc_not_a_query_per_repo(db):
    repos = _repos(db, RepoRepository).list_repos(repo_names=frozenset({"acme/r0", "acme/r1", "acme/r2"}))
    assert [(r["name"], r["acsScore"], r["status"]) for r in repos] == [
        ("r0", 100.0, "healthy"),   # latest review is running: no score yet
        ("r1", 70.0, "warning"),
        ("r2", 100.0, "healthy"),   # no reviews
    ]
    assert not db.queries_on("reviews")
    assert [q[1] for q in db.queries if q[0] == "rpc"] == ["latest_review_per_repo"]
    assert all(cols != "*" for table, cols in db.selects if table == "repositories")


@pytest.mark.parametrize("call", [
    lambda r: r.list_reviews(repo_names=frozenset({"acme/r0"})),
    lambda r: r.list_hitl_pending(repo_names=frozenset({"acme/r1"})),
    lambda r: r.get_review("a"),
    lambda r: r.get_ledger_stats("acme/r0"),
    lambda r: r.get_ledger_trend("acme/r0"),
], ids=["list_reviews", "list_hitl_pending", "get_review", "ledger_stats", "ledger_trend"])
def test_reads_never_select_star_or_the_raw_diff(db, call):
    call(_repos(db, ReviewRepository))
    selects = [cols for table, cols in db.selects if table == "reviews"]
    assert selects and all(cols != "*" and "diff_text" not in cols for cols in selects)


@pytest.mark.parametrize("call", [
    lambda r: r.list_reviews(repo_names=frozenset({"acme/r0"})),
    lambda r: r.list_hitl_pending(repo_names=frozenset({"acme/r1"})),
], ids=["list_reviews", "list_hitl_pending"])
def test_list_endpoints_never_select_the_per_file_diffs(db, call):
    call(_repos(db, ReviewRepository))
    selects = [cols for table, cols in db.selects if table == "reviews"]
    assert selects and all(cols != "*" and "diffs" not in cols for cols in selects)


def test_review_detail_still_carries_what_the_page_shows(db):
    review = _repos(db, ReviewRepository).get_review("a")
    assert review["diffs"] == [{"file": "x"}] and review["repo_name"] == "r0" and review["acs_score"] == 90.0


@pytest.mark.asyncio
async def test_daily_retention_prunes_diffs_older_than_30_days(db, monkeypatch):
    import app.worker as worker_module
    import app.repositories.dashboard as dashboard_module
    monkeypatch.setattr(dashboard_module, "get_supabase", lambda: db)
    [job] = [c for c in worker_module.WorkerSettings.cron_jobs if "prune_old_review_diffs" in c.name]
    assert job.hour is not None and job.minute is not None  # once a day
    pruned = await worker_module.prune_old_review_diffs({})
    assert pruned == 1
    old = next(r for r in db.tables["reviews"] if r["id"] == "a")
    assert old["diff_text"] is None and old["diffs"] is None
    assert next(r for r in db.tables["reviews"] if r["id"] == "d")["diff_text"] == "+huge diff"
    assert ("rpc", "prune_review_diffs", (("older_than_days", 30),)) in db.queries
