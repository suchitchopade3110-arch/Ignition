"""
P2 "Naive datetime.utcnow()": deprecated in Python 3.12 (the suite warned
about it) and naive. Every timestamp is now datetime.now(timezone.utc).
"""
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

from app.repositories.dashboard import ReviewRepository
from tests.fake_supabase import FakeSupabase

REPO = Path(__file__).resolve().parents[1]
NAIVE = "datetime." + "utcnow"  # split so this file doesn't match its own gate


def test_no_naive_utcnow_anywhere_in_python():
    found = subprocess.run(["git", "grep", "-n", NAIVE, "--", "*.py"], cwd=REPO, capture_output=True, text=True)
    assert found.stdout == "", found.stdout


def test_completed_reviews_get_an_aware_completed_at_and_a_correct_duration():
    created = (datetime.now(timezone.utc) - timedelta(seconds=90)).isoformat()
    db = FakeSupabase({"reviews": [{"id": "r1", "repo_full_name": "acme/widgets", "pr_number": 1, "title": "t",
                                    "author": "a", "branch": "b", "commit_sha": "c", "status": "running",
                                    "severity": "none", "created_at": created}]})
    repo = ReviewRepository.__new__(ReviewRepository)
    repo._db = db
    repo.update_review("r1", {"status": "completed"})
    row = db.tables["reviews"][0]
    completed_at = datetime.fromisoformat(row["completed_at"])
    assert completed_at.tzinfo is not None and completed_at.utcoffset() == timedelta(0)
    assert row["duration"] in ("1m 30s", "1m 31s")
