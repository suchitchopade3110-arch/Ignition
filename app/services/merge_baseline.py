"""
Merge baselines (audit P0-7). Regression detection compares a PR's ACS to
the repo's baseline, and nothing ever wrote one, so it never fired. When a
PR merges, this Arq job records that PR's last completed ACS in
architecture_ledger. The webhook enqueues it with
_job_id=f"baseline:{repo}:{pr}", so a redelivered "closed" event can't
double-write while Arq remembers the job; the job also skips a PR that
already has a baseline row, for redeliveries after that.
"""
import asyncio
import logging

from app.repositories.ledger import LedgerRepository

logger = logging.getLogger(__name__)


def _record(repo_full_name: str, pr_number: int, head_sha: str) -> bool:
    from app.services.review_pipeline import review_repo

    acs = review_repo.get_last_completed_acs(repo_full_name, pr_number)
    if acs is None:
        logger.info("No completed review with an ACS; no baseline written",
                    extra={"repo_full_name": repo_full_name, "pr_number": pr_number})
        return False
    ledger = LedgerRepository()
    if ledger.has_baseline_for_pr(repo_full_name, pr_number):
        logger.info("Baseline for this PR already recorded",
                    extra={"repo_full_name": repo_full_name, "pr_number": pr_number})
        return False
    ledger.write_baseline(repo_full_name, acs, {"pr": pr_number, "sha": head_sha})
    logger.info("Merge baseline recorded", extra={"repo_full_name": repo_full_name, "pr_number": pr_number})
    return True


async def record_merge_baseline(ctx: dict, repo_full_name: str, pr_number: int, head_sha: str) -> bool:
    """Arq job. True if a baseline row was written."""
    return await asyncio.to_thread(_record, repo_full_name, pr_number, head_sha)
