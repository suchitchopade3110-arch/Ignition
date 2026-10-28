"""
Audit P0-6: rejections and failures never reached the PR. The GitHub
Checks API is now the single status signal: a check run is created when
the webhook arrives and concluded at every exit of run_review_job,
following the solutions doc's outcome table. A Checks API hiccup must
never drop the webhook.
"""
import asyncio
import json
from unittest.mock import AsyncMock, patch

import httpx
import pytest

import app.main as main_module
import app.services.review_pipeline as pipeline
from app.schemas.ast_payload import ASTAnalyzerPayload
from app.services.ast_client import ASTClient
from app.repositories.ledger import LedgerRepository
from app.services.llm_client import LLMClient
from app.services.review_pipeline import run_review_job
from tests.test_integration_webhook_review_comment import (  # noqa: F401  (fixtures)
    _sign, _webhook_payload, fake_repos, mock_arq, mock_externals,
)

HEAD = "deadbeef00000000000000000000000000000000"


@pytest.fixture(autouse=True)
def no_ledger_history():
    # A finding with a pattern_key makes the critic look up its HITL history
    # (audit P1-6); this suite has no database behind it.
    with patch.object(LedgerRepository, "get_consecutive_rejections", return_value=0):
        yield


def _payload(**overrides) -> ASTAnalyzerPayload:
    base = dict(repo_full_name="acme/widgets", pr_number=7, changed_files=["src/index.ts"], symbols=[],
                dependency_graph=[], hard_rule_violations=[], changed_packages=[])
    return ASTAnalyzerPayload(**{**base, **overrides})


def _llm_with_2b_finding(severity):
    async def complete(self, prompt, json_mode=True, agent_name="unknown"):
        if not json_mode:
            return "Narrative."
        if agent_name == "agent_2b_chaos":
            return json.dumps({"findings": [
                {"file_path": "src/index.ts", "line": 1, "description": "unguarded null", "severity": severity}]})
        return json.dumps({"findings": []})
    return complete


async def _failing_llm(self, prompt, json_mode=True, agent_name="unknown"):
    raise RuntimeError("model_decommissioned")


async def _slow_llm(self, prompt, json_mode=True, agent_name="unknown"):
    await asyncio.sleep(5)
    return json.dumps({"findings": []})


# id -> (setup(stack, gh), expected conclusion, expected title prefix, expected review status)
CASES = {
    "posted_no_findings": (lambda gh: [], "success", "No findings", "completed"),
    "posted_with_findings": (
        lambda gh: [patch.object(LLMClient, "complete", new=_llm_with_2b_finding("medium"))],
        "neutral", "1 finding, highest severity medium", "completed"),
    "direct_rejection": (
        lambda gh: [patch.object(ASTClient, "analyze_git", new=AsyncMock(return_value=_payload(
            hard_rule_violations=["Direct eval() call found in src/index.ts:2"])))],
        "failure", "Hard rule violated: Direct eval() call found in src/index.ts:2", "rejected"),
    "paused_for_hitl": (
        lambda gh: [patch.object(LLMClient, "complete", new=_llm_with_2b_finding("critical"))],
        "action_required", "Waiting for human review", "waiting_hitl"),
    "incomplete": (
        lambda gh: [patch.object(LLMClient, "complete", new=_failing_llm)],
        "neutral", "Review incomplete", "completed"),
    "exception": (
        lambda gh: [patch.object(ASTClient, "analyze_git", new=AsyncMock(side_effect=RuntimeError("analyzer down")))],
        "neutral", "Ignition could not finish", "failed"),
    "timeout": (
        lambda gh: [patch.object(LLMClient, "complete", new=_slow_llm),
                    patch.object(pipeline.settings, "review_latency_budget_seconds", 0.2)],
        "neutral", "Ignition could not finish", None),
    "superseded": (
        lambda gh: [patch.object(gh._client.get_repo.return_value.get_pull.return_value.head, "sha", "f" * 40)],
        "neutral", "Ignition could not finish: superseded by " + "f" * 40, "cancelled"),
}


async def _enqueue(mock_arq):
    body = json.dumps(_webhook_payload()).encode()
    transport = httpx.ASGITransport(app=main_module.app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post("/webhooks/github", content=body, headers={
            "Content-Type": "application/json", "X-Hub-Signature-256": _sign(body), "X-GitHub-Delivery": "checks-1"})
    assert res.status_code == 202
    return mock_arq.enqueue_job.call_args.args[1:4]


@pytest.mark.asyncio
@pytest.mark.parametrize("case", list(CASES))
async def test_every_exit_concludes_the_check_run(case, fake_repos, mock_externals, mock_arq):
    fake_review_repo, _ = fake_repos
    gh = mock_externals["github_instance"]
    setup, conclusion, title, status = CASES[case]
    event_payload, review_id, correlation_id = await _enqueue(mock_arq)
    assert fake_review_repo.rows[review_id]["check_run_id"] == 4242  # created at webhook time
    gh.create_check_run.assert_called_once_with("acme/widgets", HEAD)

    patches = setup(gh)
    for p in patches:
        p.start()
    try:
        await run_review_job({}, event_payload, review_id, correlation_id)
    finally:
        for p in patches:
            p.stop()

    gh.complete_check_run.assert_called_once()
    kwargs = gh.complete_check_run.call_args.kwargs
    assert kwargs["check_run_id"] == 4242
    assert kwargs["conclusion"] == conclusion
    assert kwargs["title"].startswith(title)
    if conclusion == "action_required":
        assert kwargs["details_url"].endswith(f"/reviews/{review_id}")
    if status:
        assert fake_review_repo.rows[review_id]["status"] == status


@pytest.mark.asyncio
async def test_cancelled_job_concludes_the_check_run_and_still_reraises(fake_repos, mock_externals, mock_arq):
    gh = mock_externals["github_instance"]
    event_payload, review_id, correlation_id = await _enqueue(mock_arq)
    with patch.object(ASTClient, "analyze_git", new=AsyncMock(side_effect=asyncio.CancelledError())):
        with pytest.raises(asyncio.CancelledError):
            await run_review_job({}, event_payload, review_id, correlation_id)
    kwargs = gh.complete_check_run.call_args.kwargs
    assert (kwargs["conclusion"], kwargs["title"].startswith("Ignition could not finish")) == ("neutral", True)


@pytest.mark.asyncio
async def test_direct_rejection_posts_its_reason_on_the_pr(fake_repos, mock_externals, mock_arq):
    gh = mock_externals["github_instance"]
    event_payload, review_id, correlation_id = await _enqueue(mock_arq)
    with patch.object(ASTClient, "analyze_git", new=AsyncMock(return_value=_payload(
            hard_rule_violations=["Direct eval() call found in src/index.ts:2"]))):
        await run_review_job({}, event_payload, review_id, correlation_id)
    gh.upsert_sticky_comment.assert_called_once()
    assert "Direct eval() call found in src/index.ts:2" in gh.upsert_sticky_comment.call_args.kwargs["body"]


@pytest.mark.asyncio
async def test_a_checks_api_error_never_drops_the_webhook(fake_repos, mock_externals, mock_arq):
    fake_review_repo, _ = fake_repos
    mock_externals["github_instance"].create_check_run.side_effect = RuntimeError("Checks: Read and write not granted")
    body = json.dumps(_webhook_payload()).encode()
    transport = httpx.ASGITransport(app=main_module.app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post("/webhooks/github", content=body, headers={
            "Content-Type": "application/json", "X-Hub-Signature-256": _sign(body), "X-GitHub-Delivery": "checks-err"})
    assert res.status_code == 202 and res.json()["status"] == "queued"
    mock_arq.enqueue_job.assert_awaited_once()


# --- after a human decides, the paused check leaves action_required ---------

from tests.test_hitl_and_stream import fake_review, override_auth  # noqa: E402,F401  (fixtures)
from app.services.stream_manager import stream_manager  # noqa: E402


async def _hitl(action, gh):
    with patch("app.services.github_client.GitHubClient", return_value=gh), \
         patch.object(stream_manager, "publish", new=AsyncMock()):
        transport = httpx.ASGITransport(app=main_module.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.post(f"/api/hitl/review-1/{action}")


def _paused_gh():
    from unittest.mock import MagicMock
    gh = MagicMock()
    gh.get_pr_head_sha.return_value = HEAD
    gh.upsert_sticky_comment.return_value = {"id": 1, "html_url": "https://x/1"}
    return gh


@pytest.mark.asyncio
async def test_approving_concludes_the_check_with_what_was_posted(override_auth, fake_review):
    fake_review["review-1"].update({"commit_sha": HEAD, "check_run_id": 77})
    gh = _paused_gh()
    assert (await _hitl("approve", gh)).status_code == 200
    kwargs = gh.complete_check_run.call_args.kwargs
    assert (kwargs["check_run_id"], kwargs["conclusion"]) == (77, "neutral")
    assert kwargs["title"] == "3 findings, highest severity high"


@pytest.mark.asyncio
async def test_rejecting_concludes_the_check_as_dismissed(override_auth, fake_review):
    fake_review["review-1"].update({"commit_sha": HEAD, "check_run_id": 77})
    gh = _paused_gh()
    assert (await _hitl("reject", gh)).status_code == 200
    kwargs = gh.complete_check_run.call_args.kwargs
    assert (kwargs["check_run_id"], kwargs["conclusion"], kwargs["title"]) == (
        77, "neutral", "Review dismissed by a maintainer")


@pytest.mark.asyncio
async def test_approving_an_incomplete_review_concludes_review_incomplete(override_auth, fake_review):
    fake_review["review-1"].update({"commit_sha": HEAD, "check_run_id": 77,
                                    "status_reason": "incomplete: one or more agents failed"})
    gh = _paused_gh()
    assert (await _hitl("approve", gh)).status_code == 200
    kwargs = gh.complete_check_run.call_args.kwargs
    assert (kwargs["conclusion"], kwargs["title"]) == ("neutral", "Review incomplete")
