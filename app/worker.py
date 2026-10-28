"""
Arq worker entrypoint. Run with:

    arq app.worker.WorkerSettings

This is the process that actually executes review runs — app/main.py only
enqueues jobs (`app/services/redis_client.py::get_arq_pool`), it no longer
runs the LangGraph pipeline itself. See app/services/review_pipeline.py
for the job function.

Task registry + graceful shutdown (Phase 2 Prompt 3): deliberately not a
new tracking system — "the registry" is just the reviews.status/job_id
columns already in Supabase plus Arq's own job store, cross-referenced by
app/services/reconciliation.py at startup. The two failure modes are
handled in two different, precise places:
  - Ungraceful kill (kill -9, OOM): the process gets no chance to run any
    cleanup code, so reconciliation runs at startup instead, catching
    anything left at "running" whose job Arq no longer considers active.
  - Graceful SIGTERM with a bounded drain: `job_completion_wait` below
    tells Arq to stop picking up new jobs and wait up to that many seconds
    for in-flight jobs to finish before cancelling them. If cancelled,
    run_review_job's own CancelledError handler (review_pipeline.py) marks
    the review failed immediately, with a reason — more precise than
    waiting for the next startup's reconciliation pass to catch it.

Note: Arq's signal handling relies on asyncio's loop.add_signal_handler,
which Windows does not support — SIGTERM won't trigger the drain path on
Windows. Verified instead inside an actual Linux container (Docker
Desktop's containers are real Linux even on a Windows host), since
production (the Dockerfile) runs Linux.
"""
import asyncio
import logging
import os

from arq.connections import RedisSettings
from arq import cron
from arq.worker import func

from app.config import get_settings
from app.services.redis_client import get_redis_settings
from app.services.review_pipeline import run_review_job
from app.services.merge_baseline import record_merge_baseline
from app.services.reconciliation import reconcile_cron, reconcile_orphaned_reviews
from app.services.logging_config import configure_logging
from app.services.llm_client import get_llm_client
from app.services.schema_check import require_tables_or_exit

# Arq's own CLI doesn't call logging.basicConfig for us (unlike
# app/main.py, which does) — without this, reconciliation's INFO-level
# logging below is silently dropped at the default WARNING root level.
# configure_logging (not logging.basicConfig) so this process also emits
# structured JSON with the correlation ID, same as the FastAPI process.
configure_logging()
logger = logging.getLogger(__name__)
# Same production-safety check app/main.py runs — the worker is an
# independent entrypoint (`arq app.worker.WorkerSettings`) that never goes
# through app/main.py's module body, so it needs its own call site.
get_settings().validate_production_safety(logger)


async def on_startup(ctx: dict) -> None:
    # Constructed once here, at worker boot — every agent node
    # (app/graph/nodes/*.py) calls the same get_llm_client() getter, so
    # this just forces that first construction to happen deterministically
    # at startup instead of on whichever job/agent happens to call it
    # first.
    get_llm_client()
    # Refuse to start on a database missing a migration (audit P0-9), before
    # reconciliation or any job touches it.
    require_tables_or_exit()
    await reconcile_orphaned_reviews()


async def purge_expired_sessions(ctx: dict) -> int:
    """Daily: DELETE FROM sessions WHERE expires_at < now() (audit P1-1).
    Expired sessions are already refused at read time; this keeps their
    encrypted tokens from piling up."""
    from app.repositories.auth import AuthRepository

    removed = await asyncio.to_thread(AuthRepository().purge_expired_sessions)
    logger.info("Purged expired sessions", extra={"removed": removed})
    return removed


async def prune_old_review_diffs(ctx: dict) -> int:
    """Daily retention (I-10): stored diffs older than 30 days are dropped;
    the review rows, scores and findings stay."""
    from app.repositories.dashboard import ReviewRepository

    pruned = await asyncio.to_thread(ReviewRepository().prune_old_diffs, 30)
    logger.info("Pruned old review diffs", extra={"pruned": pruned})
    return pruned


class WorkerSettings:
    # max_tries=1: a job cancelled by the shutdown drain timeout (or one
    # that raises) is a hard, final failure — run_review_job's
    # CancelledError handler already marks the review "failed" with a
    # reason, and that needs to stick. Arq's default (retry_jobs=True,
    # max_tries=5) would silently re-enqueue the identical job for a later
    # worker to pick up, flipping the review back to "running" with no new
    # webhook — surprising given Phase 1's dedupe design assumes exactly
    # one execution per review. A human re-triggering via a fresh webhook/
    # PR sync is the intended recovery path, not a background auto-retry.
    functions = [func(run_review_job, max_tries=1), func(record_merge_baseline)]
    cron_jobs = [
        cron(purge_expired_sessions, hour=3, minute=17),
        cron(prune_old_review_diffs, hour=3, minute=41),
        # Every minute (I-4); unique, so only one worker runs it at a time.
        cron(reconcile_cron, second=0, unique=True),
    ]
    redis_settings: RedisSettings = get_redis_settings()
    on_startup = on_startup

    # Bounded drain: on SIGTERM/SIGINT, stop accepting new jobs and give
    # in-flight jobs up to this many seconds to finish before cancelling
    # them. 50 s (I-3) fits inside render.yaml's maxShutdownDelaySeconds: 60
    # for ignition-worker, so Render doesn't SIGKILL mid-drain.
    job_completion_wait = 50

    # Budgets (I-7). Two reviews at a time per 1c-2g worker (Arq's default
    # is 10); a job's whole run is capped at 220 s inside run_review_job
    # (review_pipeline.JOB_BUDGET_SECONDS), so Arq's own 240 s limit (its
    # default is 300) only ever catches something that ignores that budget.
    max_jobs = int(os.getenv("WORKER_MAX_JOBS", "2"))
    job_timeout = 240
