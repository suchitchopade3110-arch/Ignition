"""
I-4: a new worker used to kill the old worker's in-flight jobs (startup
reconciliation treated any in_progress job as dead), and rows could sit at
"queued" or "posting" forever. Now:
  - each running job refreshes SETEX review_hb:{review_id} 30 every 10 s;
  - reconciliation runs at startup and every minute:
      running, no heartbeat        -> failed, review.failed published
      queued > 10 min, no live job -> re-enqueued once, then failed
      posting > 5 min              -> back to waiting_hitl
  - the webhook marks the row failed and answers 503 if enqueueing fails.
"""
import asyncio
import json
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from arq.jobs import JobStatus

import app.main as main_module
import app.services.reconciliation as reconciliation
from app.services.review_pipeline import review_repo
from tests.fake_supabase import FakeAsyncRedis, FakeSupabase
from tests.test_integration_webhook_review_comment import (  # noqa: F401  (fixtures)
    _sign, _webhook_payload, fake_repos, mock_arq, mock_externals,
)


def _ago(minutes):
    return (datetime.now(timezone.utc) - timedelta(minutes=minutes)).isoformat()


def _row(rid, status, job_id=None, created=1, **extra):
    return {"id": rid, "repo_full_name": "acme/widgets", "pr_number": 7, "commit_sha": "a" * 40, "title": "t",
            "status": status, "job_id": job_id, "created_at": _ago(created), "correlation_id": f"c-{rid}", **extra}


class World:
    def __init__(self, monkeypatch, rows, job_statuses=None, heartbeats=()):
        self.db = FakeSupabase({"reviews": rows})
        self.redis = FakeAsyncRedis()
        for rid in heartbeats:
            self.redis.store[f"review_hb:{rid}"] = "worker-old"
        self.pool = MagicMock()
        self.pool.get = self.redis.get
        self.pool.enqueue_job = AsyncMock(return_value=MagicMock(job_id="requeued-job"))
        self.published = []
        statuses = job_statuses or {}

        def make_job(job_id, redis):
            job = MagicMock()
            job.status = AsyncMock(return_value=statuses.get(job_id, JobStatus.not_found))
            return job

        async def publish(review_id, event):
            self.published.append((review_id, event["type"]))

        repo = MagicMock(wraps=review_repo)
        repo._db, repo.TABLE = self.db, "reviews"
        repo.update_review = lambda rid, upd: self.db.table("reviews").update(upd).eq("id", rid).execute()
        monkeypatch.setattr(reconciliation, "ReviewRepository", lambda: repo)
        monkeypatch.setattr(reconciliation, "get_arq_pool", AsyncMock(return_value=self.pool))
        monkeypatch.setattr(reconciliation, "Job", make_job)
        from app.services.stream_manager import stream_manager
        monkeypatch.setattr(stream_manager, "publish", publish)

    def row(self, rid):
        return next(r for r in self.db.tables["reviews"] if r["id"] == rid)


@pytest.mark.asyncio
async def test_a_running_review_with_a_live_heartbeat_is_left_alone(monkeypatch):
    # The old worker is still draining it during a deploy: Arq says
    # in_progress, but the heartbeat proves someone is working on it.
    w = World(monkeypatch, [_row("r1", "running", "job-1")], {"job-1": JobStatus.in_progress}, heartbeats={"r1"})
    await reconciliation.reconcile_orphaned_reviews()
    assert w.row("r1")["status"] == "running" and w.published == []


@pytest.mark.asyncio
async def test_a_running_review_without_a_heartbeat_fails_and_tells_the_dashboard(monkeypatch):
    w = World(monkeypatch, [_row("r1", "running", "job-1")], {"job-1": JobStatus.in_progress})
    assert await reconciliation.reconcile_orphaned_reviews() >= 1
    assert w.row("r1")["status"] == "failed" and w.row("r1")["status_reason"]
    assert ("r1", "review.failed") in w.published


@pytest.mark.asyncio
async def test_a_stale_queued_review_with_no_live_job_is_requeued_once(monkeypatch):
    event = {"action": "opened", "pull_request": {"number": 7}}
    w = World(monkeypatch, [_row("r1", "queued", "job-lost", created=11, event_payload=event)])
    await reconciliation.reconcile_orphaned_reviews()
    w.pool.enqueue_job.assert_awaited_once()
    args, kwargs = w.pool.enqueue_job.await_args.args, w.pool.enqueue_job.await_args.kwargs
    assert args == ("run_review_job", event, "r1", "c-r1")
    assert kwargs["_job_id"].endswith(":requeued")
    row = w.row("r1")
    assert row["status"] == "queued" and row["job_id"] == "requeued-job"
    assert row["status_reason"] == reconciliation.REQUEUED_REASON


@pytest.mark.asyncio
async def test_a_requeued_review_that_is_lost_again_fails(monkeypatch):
    w = World(monkeypatch, [_row("r1", "queued", "requeued-job", created=25, event_payload={},
                                 status_reason=reconciliation.REQUEUED_REASON)])
    await reconciliation.reconcile_orphaned_reviews()
    w.pool.enqueue_job.assert_not_awaited()
    assert w.row("r1")["status"] == "failed" and ("r1", "review.failed") in w.published


@pytest.mark.asyncio
@pytest.mark.parametrize("created, job_status", [(3, JobStatus.not_found), (30, JobStatus.queued),
                                                 (30, JobStatus.deferred), (30, JobStatus.in_progress)])
async def test_a_queued_review_that_is_young_or_has_a_live_job_is_left_alone(monkeypatch, created, job_status):
    w = World(monkeypatch, [_row("r1", "queued", "job-1", created=created, event_payload={})], {"job-1": job_status})
    await reconciliation.reconcile_orphaned_reviews()
    w.pool.enqueue_job.assert_not_awaited()
    assert w.row("r1")["status"] == "queued" and w.published == []


@pytest.mark.asyncio
async def test_a_stuck_posting_claim_goes_back_to_waiting_hitl(monkeypatch):
    w = World(monkeypatch, [_row("old", "posting", status_changed_at=_ago(6)),
                            _row("new", "posting", status_changed_at=_ago(1))])
    await reconciliation.reconcile_orphaned_reviews()
    assert w.row("old")["status"] == "waiting_hitl"
    assert w.row("new")["status"] == "posting"


def test_reconciliation_runs_every_minute_on_the_worker():
    import app.worker as worker_module
    [job] = [c for c in worker_module.WorkerSettings.cron_jobs if "reconcile" in c.name]
    assert job.minute is None and job.hour is None and job.second == 0 and job.unique


# --- the heartbeat ------------------------------------------------------------

@pytest.mark.asyncio
async def test_a_running_job_keeps_its_heartbeat_fresh_and_clears_it_at_the_end(monkeypatch, fake_repos,
                                                                                mock_externals, mock_arq):
    from app.services import review_pipeline as pipeline
    monkeypatch.setattr(pipeline, "HEARTBEAT_INTERVAL_SECONDS", 0.05)
    redis = FakeAsyncRedis()
    seen = []
    real_setex = redis.setex

    async def setex(key, ttl, value):
        seen.append((key, ttl))
        await real_setex(key, ttl, value)
    redis.setex = setex

    async def slow_analyzer(*a, **k):
        await asyncio.sleep(0.2)
        raise RuntimeError("stop here")
    body = json.dumps(_webhook_payload()).encode()
    transport = httpx.ASGITransport(app=main_module.app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        await client.post("/webhooks/github", content=body, headers={
            "Content-Type": "application/json", "X-Hub-Signature-256": _sign(body), "X-GitHub-Delivery": "hb-1"})
    event_payload, review_id, correlation_id = mock_arq.enqueue_job.call_args.args[1:4]
    with patch.object(pipeline.ast_client, "analyze_git", new=slow_analyzer):
        await pipeline.run_review_job({"redis": redis}, event_payload, review_id, correlation_id)
    assert len(seen) >= 2 and all(entry == (f"review_hb:{review_id}", 30) for entry in seen)
    assert f"review_hb:{review_id}" not in redis.store


# --- the webhook ------------------------------------------------------------------

@pytest.mark.asyncio
async def test_an_enqueue_failure_is_a_503_and_a_failed_row(fake_repos, mock_externals, mock_arq):
    fake_review_repo, _ = fake_repos
    mock_arq.enqueue_job.side_effect = ConnectionError("redis down")
    body = json.dumps(_webhook_payload()).encode()
    transport = httpx.ASGITransport(app=main_module.app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post("/webhooks/github", content=body, headers={
            "Content-Type": "application/json", "X-Hub-Signature-256": _sign(body), "X-GitHub-Delivery": "enq-1"})
    assert res.status_code == 503
    [row] = fake_review_repo.rows.values()
    assert row["status"] == "failed" and "enqueue" in row["status_reason"]


@pytest.mark.asyncio
async def test_the_webhook_stores_the_event_for_a_later_requeue(fake_repos, mock_externals, mock_arq):
    fake_review_repo, _ = fake_repos
    body = json.dumps(_webhook_payload()).encode()
    transport = httpx.ASGITransport(app=main_module.app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        await client.post("/webhooks/github", content=body, headers={
            "Content-Type": "application/json", "X-Hub-Signature-256": _sign(body), "X-GitHub-Delivery": "store-1"})
    [row] = fake_review_repo.rows.values()
    assert row["event_payload"] == mock_arq.enqueue_job.call_args.args[1]


@pytest.mark.asyncio
async def test_the_approve_claim_records_when_posting_started():
    from tests.test_hitl_and_stream import _FAKE_USER  # noqa: F401
    db = FakeSupabase({"reviews": [_row("r1", "waiting_hitl", installation_id=1, final_comment_markdown="x")]})
    with patch.object(review_repo, "_db", db), \
         patch("app.services.github_client.GitHubClient", side_effect=RuntimeError("github down")):
        from app.auth import get_current_user, require_review_repo_access
        from app.security import verify_csrf_token
        overrides = {get_current_user: lambda: _FAKE_USER, require_review_repo_access: lambda: _FAKE_USER,
                     verify_csrf_token: lambda: None}
        main_module.app.dependency_overrides.update(overrides)
        claim_updates = []
        real_table = db.table

        def spy(name):
            query = real_table(name)
            real_update = query.update

            def update(values):
                claim_updates.append(dict(values))
                return real_update(values)
            query.update = update
            return query
        db.table = spy
        try:
            transport = httpx.ASGITransport(app=main_module.app)
            async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                await client.post("/api/hitl/r1/approve")
        finally:
            for key in overrides:
                main_module.app.dependency_overrides.pop(key, None)
    claim = next(u for u in claim_updates if u.get("status") == "posting")
    assert datetime.fromisoformat(claim["status_changed_at"]) > datetime.now(timezone.utc) - timedelta(minutes=1)
