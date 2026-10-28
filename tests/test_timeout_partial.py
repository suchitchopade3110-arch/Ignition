"""
P2 "Timeout posts an empty approval": a review that ran past
review_latency_budget_seconds was parked in the HITL queue as critical, and
approving it posted an empty review. Now a timeout never goes to HITL: the
review ends failed ("timed out after N s"), the check run concludes neutral
with that title, and the sticky comment is updated with whatever the
Critic verified before the cut-off, marked incomplete.
"""
import threading
import time
from unittest.mock import patch

import pytest

import app.services.review_pipeline as pipeline
from app.repositories.ledger import LedgerRepository
from app.services.llm_client import LLMClient
from app.services.review_pipeline import run_review_job
from tests.test_check_runs import HEAD, _enqueue, _llm_with_2b_finding, _slow_llm
from tests.test_integration_webhook_review_comment import (  # noqa: F401  (fixtures)
    fake_repos, mock_arq, mock_externals,
)


@pytest.fixture(autouse=True)
def no_ledger_history():
    with patch.object(LedgerRepository, "get_consecutive_rejections", return_value=0):
        yield


async def _run(mock_arq, budget, llm):
    event_payload, review_id, correlation_id = await _enqueue(mock_arq)
    with patch.object(LLMClient, "complete", new=llm), \
         patch.object(pipeline.settings, "review_latency_budget_seconds", budget):
        await run_review_job({}, event_payload, review_id, correlation_id)
    return review_id


@pytest.mark.asyncio
async def test_timeout_before_the_critic_is_not_routed_to_hitl(fake_repos, mock_externals, mock_arq):
    fake_review_repo, _ = fake_repos
    gh = mock_externals["github_instance"]
    review_id = await _run(mock_arq, 0.2, _slow_llm)

    row = fake_review_repo.rows[review_id]
    assert row["status"] == "failed"
    assert row["status_reason"] == "timed out after 0.2 s"
    assert row.get("hitl_severity") != "critical"

    kwargs = gh.complete_check_run.call_args.kwargs
    assert kwargs["conclusion"] == "neutral" and "timed out after 0.2 s" in kwargs["title"]

    [call] = gh.upsert_sticky_comment.call_args_list
    body = call.kwargs["body"]
    assert "incomplete" in body.lower() and "timed out after 0.2 s" in body
    assert "No findings were verified before the timeout" in body
    assert "Clean pass" not in body and "No findings." != body.strip()
    assert row["final_comment_markdown"] == body


@pytest.mark.asyncio
async def test_timeout_after_the_critic_posts_what_was_verified(fake_repos, mock_externals, mock_arq):
    fake_review_repo, _ = fake_repos
    gh = mock_externals["github_instance"]
    calls = {"n": 0}
    lock = threading.Lock()

    def head_sha(repo, pr):
        # finalize_and_post's check before posting hangs past the budget (and
        # then sees a newer head, so its own post never happens); the timeout
        # path's check answers at once.
        with lock:
            calls["n"] += 1
            first = calls["n"] == 1
        if first:
            time.sleep(2)
            return "f" * 40
        return HEAD
    gh.get_pr_head_sha.side_effect = head_sha

    review_id = await _run(mock_arq, 1.0, _llm_with_2b_finding("medium"))

    row = fake_review_repo.rows[review_id]
    assert (row["status"], row["status_reason"]) == ("failed", "timed out after 1 s")
    [call] = gh.upsert_sticky_comment.call_args_list
    body = call.kwargs["body"]
    assert "incomplete" in body.lower()
    assert "unguarded null" in body and "src/index.ts:1" in body and "medium" in body
    assert "timed out after 1 s" in gh.complete_check_run.call_args.kwargs["title"]


@pytest.mark.asyncio
async def test_a_newer_push_means_the_timed_out_comment_is_not_posted(fake_repos, mock_externals, mock_arq):
    fake_review_repo, _ = fake_repos
    gh = mock_externals["github_instance"]
    gh.get_pr_head_sha.return_value = "f" * 40
    review_id = await _run(mock_arq, 0.2, _slow_llm)
    gh.upsert_sticky_comment.assert_not_called()
    assert fake_review_repo.rows[review_id]["status"] == "failed"
