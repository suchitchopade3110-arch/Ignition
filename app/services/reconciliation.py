"""
Startup reconciliation for the Arq worker: detects review rows left at
"running" by a worker process that died mid-job (kill -9, OOM kill, host
eviction — anything that gave the process no chance to run its own
cleanup code) and marks them failed instead of leaving them orphaned.

Deliberately not a new tracking system — per the Phase 2 scope for this
task, "the task registry" here just means cross-referencing two things
that already exist: the `reviews.status`/`reviews.job_id` columns
(Supabase) and Arq's own job result store (Redis, already backing the
queue). A review is orphaned if it says "running" but Arq no longer has
any record of that job actually being in flight.

The complementary half — jobs cut off by a *graceful* shutdown's drain
timeout — is handled separately and more precisely in
app/services/review_pipeline.py::run_review_job's own CancelledError
handler, since that code knows exactly which job it is at the moment it's
cancelled. This module only ever needs to run at startup, to clean up
after a restart.
"""
import logging

from arq.jobs import Job, JobStatus

from app.repositories.dashboard import ReviewRepository
from app.services.redis_client import get_arq_pool

logger = logging.getLogger(__name__)

# Job states that mean "not this worker's problem — leave it alone."
# `in_progress` is deliberately NOT included: Arq sets a job to
# in_progress when a worker starts it and only ever updates it again once
# that worker's own task actually finishes — there's no heartbeat/lease
# that flips it back if the worker dies uncleanly. So `in_progress` alone
# does not mean "still genuinely running"; it just means "some worker
# claimed this and never reported back."
#
# This reconciliation only runs at THIS worker's own startup, before its
# main dispatch loop has claimed anything — so in a single-worker-replica
# topology (this project's actual deployment shape: one `worker` service,
# not a fleet), any job still showing in_progress at that exact moment
# cannot legitimately be "being worked on right now" by anyone, because
# the only worker in existence just started. Treating in_progress as
# orphaned here is therefore correct for this topology, not just a
# simplification — verified live: a job killed mid-execution still reads
# back as in_progress from Arq after the process is gone.
#
# This assumption would need revisiting (a heartbeat/lease per job, not
# just per worker) if this ever scales to multiple concurrent worker
# replicas — flagging that boundary rather than silently baking it in.
_NOT_ORPHANED_JOB_STATUSES = {JobStatus.deferred, JobStatus.queued}


async def reconcile_orphaned_reviews() -> int:
    """Runs once at Arq worker startup. Returns the number of reviews
    reconciled (marked failed), for logging/visibility."""
    review_repo = ReviewRepository()
    redis = await get_arq_pool()

    res = review_repo._db.table(review_repo.TABLE).select("id, job_id").eq("status", "running").execute()
    running_reviews = res.data or []

    reconciled = 0
    for row in running_reviews:
        review_id = row["id"]
        job_id = row.get("job_id")

        is_orphaned = job_id is None
        if not is_orphaned:
            job = Job(job_id, redis)
            status = await job.status()
            is_orphaned = status not in _NOT_ORPHANED_JOB_STATUSES

        if is_orphaned:
            logger.warning(
                "Reconciling orphaned review %s (job_id=%s) — marking failed",
                review_id, job_id,
            )
            review_repo.update_review(
                review_id,
                {
                    "status": "failed",
                    "status_reason": "interrupted — process restarted",
                },
            )
            reconciled += 1

    if reconciled:
        logger.info("Startup reconciliation: %d orphaned review(s) marked failed", reconciled)
    else:
        logger.info("Startup reconciliation: no orphaned reviews found")

    return reconciled
