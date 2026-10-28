"""
P2 "Partial success reported as failure": auto-fix suggestions went out
before the summary, and a summary post that failed failed the whole review.
Now the summary is posted first and the suggestions after it; if posting
the summary still fails after retries, the review stays completed with
status_reason "comment not posted", the check run carries the result, and
no suggestions are posted on their own.
"""
import json
from unittest.mock import patch

import pytest

import app.graph.workflow as workflow
from app.repositories.ledger import LedgerRepository
from app.services.llm_client import LLMClient
from app.services.review_pipeline import run_review_job
from tests.test_check_runs import _enqueue
from tests.test_integration_webhook_review_comment import (  # noqa: F401  (fixtures)
    fake_repos, mock_arq, mock_externals,
)


@pytest.fixture(autouse=True)
def fast_retries(monkeypatch):
    monkeypatch.setattr(workflow, "SUMMARY_POST_RETRY_DELAYS", (0, 0), raising=False)
    with patch.object(LedgerRepository, "get_consecutive_rejections", return_value=0):
        yield


async def _llm_with_patchable_finding(self, prompt, json_mode=True, agent_name="unknown"):
    if not json_mode:
        return "Narrative."
    if agent_name == "agent_2b_chaos":
        return json.dumps({"findings": [{
            "file_path": "src/index.ts", "line": 1, "description": "unguarded null", "severity": "medium",
            "suggested_patch": "if (x == null) return;"}]})
    return json.dumps({"findings": []})


async def _run(fake_repos, mock_arq):
    _, fake_repo_repo = fake_repos
    fake_repo_repo.settings["enable_auto_fix"] = True
    event_payload, review_id, correlation_id = await _enqueue(mock_arq)
    with patch.object(LLMClient, "complete", new=_llm_with_patchable_finding):
        await run_review_job({}, event_payload, review_id, correlation_id)
    return review_id


def _suggestion_calls(gh) -> list[int]:
    return [i for i, c in enumerate(gh.mock_calls)
            if c[0].endswith(("post_inline_suggestion", "create_review"))]


@pytest.mark.asyncio
async def test_summary_is_posted_before_any_suggestion(fake_repos, mock_externals, mock_arq):
    gh = mock_externals["github_instance"]
    review_id = await _run(fake_repos, mock_arq)
    summary = [i for i, c in enumerate(gh.mock_calls) if c[0] == "upsert_sticky_comment"]
    suggestions = _suggestion_calls(gh)
    assert summary and suggestions, gh.mock_calls
    assert summary[0] < suggestions[0]
    assert fake_repos[0].rows[review_id]["status"] == "completed"


@pytest.mark.asyncio
async def test_a_summary_that_cannot_be_posted_keeps_the_review_completed(fake_repos, mock_externals, mock_arq):
    fake_review_repo, _ = fake_repos
    gh = mock_externals["github_instance"]
    gh.upsert_sticky_comment.side_effect = RuntimeError("GitHub 502")
    review_id = await _run(fake_repos, mock_arq)

    row = fake_review_repo.rows[review_id]
    assert (row["status"], row["status_reason"]) == ("completed", "comment not posted")
    assert gh.upsert_sticky_comment.call_count == 3  # retried
    assert not _suggestion_calls(gh)  # no suggestions without their summary
    kwargs = gh.complete_check_run.call_args.kwargs
    assert (kwargs["conclusion"], kwargs["title"]) == ("neutral", "1 finding, highest severity medium")
    assert "unguarded null" in kwargs["summary"] and "could not be posted" in kwargs["summary"]


@pytest.mark.asyncio
async def test_one_failed_attempt_is_retried_and_posts(fake_repos, mock_externals, mock_arq):
    fake_review_repo, _ = fake_repos
    gh = mock_externals["github_instance"]
    ok = gh.upsert_sticky_comment.return_value
    gh.upsert_sticky_comment.side_effect = [RuntimeError("GitHub 502"), ok]
    review_id = await _run(fake_repos, mock_arq)
    row = fake_review_repo.rows[review_id]
    assert (row["status"], row.get("status_reason")) == ("completed", None)
    assert gh.upsert_sticky_comment.call_count == 2
