"""
app.services.reconciliation.reconcile_orphaned_reviews — startup cleanup
for review rows left at "running" by a worker that died mid-job.
Previously untested despite being the sole mechanism recovering from an
ungraceful worker kill (see the module's own docstring).

Note: reconcile_orphaned_reviews constructs its own `ReviewRepository()`
rather than using the app.services.review_pipeline singleton (unlike the
webhook/HITL routes) — so these tests patch
app.services.reconciliation.ReviewRepository itself, not that singleton.
"""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from arq.jobs import JobStatus

from app.services.reconciliation import reconcile_orphaned_reviews


def _fake_review_repo(rows: list[dict], updates: dict) -> MagicMock:
    repo = MagicMock()
    repo.TABLE = "reviews"
    repo._db.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(data=rows)
    repo.update_review.side_effect = lambda review_id, u: updates.setdefault(review_id, u)
    return repo


@pytest.mark.asyncio
async def test_no_running_reviews_reconciles_nothing():
    updates = {}
    fake_repo = _fake_review_repo([], updates)
    with patch("app.services.reconciliation.ReviewRepository", return_value=fake_repo), \
         patch("app.services.reconciliation.get_arq_pool", new=AsyncMock(return_value=AsyncMock())):
        count = await reconcile_orphaned_reviews()
    assert count == 0
    assert updates == {}


@pytest.mark.asyncio
async def test_review_with_no_job_id_is_orphaned():
    """job_id=None means the review was created but never actually got
    enqueued (or the enqueue result was lost) — orphaned by definition,
    no Job lookup needed."""
    updates = {}
    fake_repo = _fake_review_repo([{"id": "review-1", "job_id": None}], updates)
    with patch("app.services.reconciliation.ReviewRepository", return_value=fake_repo), \
         patch("app.services.reconciliation.get_arq_pool", new=AsyncMock(return_value=AsyncMock())):
        count = await reconcile_orphaned_reviews()

    assert count == 1
    assert updates["review-1"]["status"] == "failed"
    assert "status_reason" in updates["review-1"]


@pytest.mark.asyncio
async def test_review_with_deferred_job_is_not_orphaned():
    """deferred/queued means genuinely still pending, not a crash victim —
    must be left alone."""
    updates = {}
    fake_repo = _fake_review_repo([{"id": "review-1", "job_id": "job-abc"}], updates)
    fake_job = MagicMock()
    fake_job.status = AsyncMock(return_value=JobStatus.queued)
    with patch("app.services.reconciliation.ReviewRepository", return_value=fake_repo), \
         patch("app.services.reconciliation.get_arq_pool", new=AsyncMock(return_value=AsyncMock())), \
         patch("app.services.reconciliation.Job", return_value=fake_job):
        count = await reconcile_orphaned_reviews()

    assert count == 0
    assert updates == {}


@pytest.mark.asyncio
async def test_review_with_in_progress_job_is_orphaned():
    """in_progress does NOT mean genuinely still running — see the
    module's own docstring on why this single-worker-replica topology
    makes that assumption correct here."""
    updates = {}
    fake_repo = _fake_review_repo([{"id": "review-1", "job_id": "job-abc"}], updates)
    fake_job = MagicMock()
    fake_job.status = AsyncMock(return_value=JobStatus.in_progress)
    with patch("app.services.reconciliation.ReviewRepository", return_value=fake_repo), \
         patch("app.services.reconciliation.get_arq_pool", new=AsyncMock(return_value=AsyncMock())), \
         patch("app.services.reconciliation.Job", return_value=fake_job):
        count = await reconcile_orphaned_reviews()

    assert count == 1
    assert updates["review-1"]["status"] == "failed"


@pytest.mark.asyncio
async def test_multiple_reviews_only_orphaned_ones_reconciled():
    updates = {}
    fake_repo = _fake_review_repo([
        {"id": "orphan-1", "job_id": None},
        {"id": "still-queued", "job_id": "job-queued"},
        {"id": "orphan-2", "job_id": "job-dead"},
    ], updates)

    statuses_by_job_id = {"job-queued": JobStatus.queued, "job-dead": JobStatus.in_progress}

    def make_job(job_id, _redis):
        job = MagicMock()
        # AsyncMock(side_effect=<sync callable>) does NOT await a coroutine
        # returned by that callable — it treats the coroutine object itself
        # as the result. return_value (not side_effect) is what's actually
        # awaited-and-returned correctly here for a fixed-per-instance value.
        job.status = AsyncMock(return_value=statuses_by_job_id[job_id])
        return job

    with patch("app.services.reconciliation.ReviewRepository", return_value=fake_repo), \
         patch("app.services.reconciliation.get_arq_pool", new=AsyncMock(return_value=AsyncMock())), \
         patch("app.services.reconciliation.Job", side_effect=make_job):
        count = await reconcile_orphaned_reviews()

    assert count == 2
    assert set(updates.keys()) == {"orphan-1", "orphan-2"}
    assert "still-queued" not in updates
