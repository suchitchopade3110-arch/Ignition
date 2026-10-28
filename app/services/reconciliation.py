"""
Reconciliation of review rows whose job is gone (I-4). Runs at worker
startup and every minute as an Arq cron (app/worker.py), so it must never
touch a review another worker is still running:

  running, no heartbeat         -> failed; review.failed published. Every
                                   running job refreshes review_hb:{id}
                                   (TTL 30 s) every 10 s
                                   (review_pipeline._heartbeat), so a
                                   missing key means the process is gone —
                                   even when Arq still says in_progress
                                   (it never learns a worker died).
  queued > 10 min, no live job  -> re-enqueued once from the stored event
                                   (reviews.event_payload), then failed.
  posting > 5 min               -> back to waiting_hitl (an approve that
                                   died between claim and post).

The complementary half — a job cancelled by a graceful shutdown's drain
timeout — is handled in run_review_job's own CancelledError handler.
"""
import asyncio
import logging
from datetime import datetime, timedelta, timezone

from arq.jobs import Job, JobStatus

from app.repositories.dashboard import ReviewRepository
from app.services import check_runs
from app.services.redis_client import get_arq_pool
from app.services.stream_manager import stream_manager

logger = logging.getLogger(__name__)

HEARTBEAT_KEY = "review_hb:{review_id}"
QUEUED_STALE_AFTER = timedelta(minutes=10)
POSTING_STALE_AFTER = timedelta(minutes=5)
REQUEUED_REASON = "re-enqueued by reconciliation (job lost)"

# Arq states meaning "a job for this review is still pending or running".
_LIVE_JOB_STATUSES = {JobStatus.deferred, JobStatus.queued, JobStatus.in_progress}
# For a running row without a heartbeat: still waiting to start is not
# orphaned; in_progress without a heartbeat is (Arq never clears it).
_NOT_ORPHANED_JOB_STATUSES = {JobStatus.deferred, JobStatus.queued}


async def _has_heartbeat(redis, review_id: str) -> bool:
    try:
        value = await redis.get(HEARTBEAT_KEY.format(review_id=review_id))
    except Exception:
        logger.warning("Heartbeat lookup failed for %s", review_id, exc_info=True)
        return True  # can't tell: leave the review alone this round
    return isinstance(value, (bytes, str))


async def _job_status(redis, job_id: str | None):
    if not job_id:
        return None
    return await Job(job_id, redis).status()


async def _fail(review_repo, row: dict, status_reason: str) -> None:
    review_id = row["id"]
    await asyncio.to_thread(review_repo.update_review, review_id, {"status": "failed", "status_reason": status_reason})
    try:
        await stream_manager.publish(review_id, {"type": "review.failed", "reviewId": review_id, "status": "failed"})
    except Exception:
        logger.warning("Could not publish review.failed for %s", review_id, exc_info=True)
    if row.get("installation_id") and row.get("commit_sha") and row.get("repo_full_name"):
        await check_runs.conclude_check_run(  # best-effort (audit P0-6)
            reviews=review_repo, review_id=review_id, installation_id=row["installation_id"],
            repo=row["repo_full_name"], head_sha=row["commit_sha"], conclusion="neutral",
            title=check_runs.could_not_finish_title(status_reason), summary=status_reason,
        )


async def _reconcile_running(review_repo, redis) -> int:
    res = await asyncio.to_thread(
        review_repo._db.table(review_repo.TABLE).select("id, job_id").eq("status", "running").execute
    )
    reconciled = 0
    for row in res.data or []:
        review_id, job_id = row["id"], row.get("job_id")
        if await _has_heartbeat(redis, review_id):
            continue  # a worker (perhaps the old one, draining) is on it
        status = await _job_status(redis, job_id)
        if status in _NOT_ORPHANED_JOB_STATUSES:
            continue
        logger.warning("Reconciling orphaned review %s (job_id=%s) — marking failed", review_id, job_id)
        await _fail(review_repo, row, "interrupted — the worker running it stopped")
        reconciled += 1
    return reconciled


async def _reconcile_queued(review_repo, redis, now: datetime) -> int:
    res = await asyncio.to_thread(
        review_repo._db.table(review_repo.TABLE)
        .select("id, job_id, status_reason, event_payload, correlation_id, repo_full_name, pr_number, "
                "commit_sha, installation_id")
        .eq("status", "queued")
        .lt("created_at", (now - QUEUED_STALE_AFTER).isoformat())
        .execute
    )
    reconciled = 0
    for row in res.data or []:
        if await _job_status(redis, row.get("job_id")) in _LIVE_JOB_STATUSES:
            continue
        review_id = row["id"]
        if row.get("status_reason") == REQUEUED_REASON or not row.get("event_payload"):
            logger.warning("Queued review %s lost its job again; marking failed", review_id)
            await _fail(review_repo, row, "failed: the review job was lost and could not be re-run")
        else:
            job = await redis.enqueue_job(
                "run_review_job", row["event_payload"], review_id, row.get("correlation_id"),
                _job_id=f"review:{row.get('repo_full_name')}:{row.get('pr_number')}:{row.get('commit_sha')}:requeued",
            )
            logger.warning("Re-enqueued queued review %s whose job was lost", review_id)
            await asyncio.to_thread(
                review_repo.update_review, review_id,
                {"job_id": job.job_id if job else None, "status_reason": REQUEUED_REASON},
            )
        reconciled += 1
    return reconciled


def _release_stuck_posting(review_repo, now: datetime) -> int:
    res = (
        review_repo._db.table(review_repo.TABLE)
        .update({"status": "waiting_hitl", "status_changed_at": now.isoformat()})
        .eq("status", "posting")
        .lt("status_changed_at", (now - POSTING_STALE_AFTER).isoformat())
        .execute()
    )
    released = len(res.data or [])
    if released:
        logger.warning("Released %d stuck posting claim(s) back to waiting_hitl", released)
    return released


async def reconcile_orphaned_reviews() -> int:
    """Returns how many reviews were changed, for logging/visibility."""
    review_repo = ReviewRepository()
    redis = await get_arq_pool()
    now = datetime.now(timezone.utc)
    reconciled = await _reconcile_running(review_repo, redis)
    reconciled += await _reconcile_queued(review_repo, redis, now)
    reconciled += await asyncio.to_thread(_release_stuck_posting, review_repo, now)
    if reconciled:
        logger.info("Reconciliation: %d review(s) changed", reconciled)
    return reconciled


async def reconcile_cron(ctx: dict) -> int:
    """Arq cron entry point (every minute)."""
    return await reconcile_orphaned_reviews()
