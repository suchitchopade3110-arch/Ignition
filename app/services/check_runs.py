"""
GitHub check runs as the single status signal for a review (audit P0-6).

A check run named "Ignition" is created when the webhook arrives and
concluded at every exit of the review job, following the solutions doc's
outcome table:

  posted, no findings            success          "No findings"
  posted with findings           neutral          "N findings, highest severity S"
  direct_rejection               failure          "Hard rule violated: <reason>"
  paused for HITL                action_required  "Waiting for human review" (+ details_url)
  incomplete (an agent failed)   neutral          "Review incomplete"
  exception, timeout, cancelled  neutral          "Ignition could not finish: <status_reason>"

Infra errors conclude neutral, not failure, so a provider outage doesn't
block every merge on repos that require the check. Every call here is
best-effort for the caller: a Checks API problem is logged, never allowed
to fail a webhook or a review.
"""
import asyncio
import logging

logger = logging.getLogger(__name__)

SEVERITY_ORDER = ["none", "low", "medium", "high", "critical"]


def posted_outcome(findings: list[dict], incomplete: bool) -> tuple[str, str]:
    """Conclusion and title for a review whose comment was posted."""
    if incomplete:
        return "neutral", "Review incomplete"
    if not findings:
        return "success", "No findings"
    highest = max(
        (f.get("severity") or "none" for f in findings),
        key=lambda s: SEVERITY_ORDER.index(s) if s in SEVERITY_ORDER else 0,
    )
    n = len(findings)
    return "neutral", f"{n} finding{'' if n == 1 else 's'}, highest severity {highest}"


def could_not_finish_title(status_reason: str) -> str:
    return f"Ignition could not finish: {status_reason}"


def create_check_run_sync(installation_id: int, repo: str, head_sha: str) -> int:
    from app.services.github_client import GitHubClient

    return GitHubClient(installation_id=installation_id).create_check_run(repo, head_sha)


def conclude_check_run_sync(*, reviews, review_id: str, installation_id: int, repo: str, head_sha: str,
                            conclusion: str, title: str, summary: str, details_url: str | None = None) -> None:
    """Completes the review's check run, creating it first if the webhook
    couldn't (so a GitHub hiccup at webhook time still ends with a signal)."""
    from app.services.github_client import GitHubClient

    gh = GitHubClient(installation_id=installation_id)
    check_run_id = reviews.get_check_run_id(review_id)
    if not check_run_id:
        check_run_id = gh.create_check_run(repo, head_sha)
        reviews.update_review(review_id, {"check_run_id": check_run_id})
    gh.complete_check_run(
        repo=repo, check_run_id=check_run_id, conclusion=conclusion,
        title=title, summary=summary or title, details_url=details_url,
    )


async def conclude_check_run(**kwargs) -> bool:
    """Best-effort async wrapper; True if GitHub accepted the conclusion."""
    try:
        await asyncio.to_thread(conclude_check_run_sync, **kwargs)
        return True
    except Exception:
        logger.exception("Could not conclude the GitHub check run", extra={"review_id": kwargs.get("review_id")})
        return False
