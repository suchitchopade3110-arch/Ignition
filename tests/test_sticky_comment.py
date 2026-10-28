"""
Audit P1-8: one Ignition comment per PR, edited in place on every push,
never a new comment each time; reviews of superseded commits are cancelled
instead of posting stale results; drafts are skipped until they are ready.
"""
import json
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

import app.main as main_module
from app.services import github_client as github_client_module
from app.services.github_client import GitHubClient

MARKER = "<!-- ignition:review -->"


def _client_with_comments(comments):
    gh = GitHubClient.__new__(GitHubClient)  # skip the token exchange
    issue = MagicMock()
    issue.get_comments.return_value = comments
    issue.create_comment.return_value = MagicMock(raw_data={"id": 99, "html_url": "https://x/new"})
    gh._client = MagicMock()
    gh._client.get_repo.return_value.get_issue.return_value = issue
    return gh, issue


def _comment(login, body, cid):
    c = MagicMock(body=body, raw_data={"id": cid, "html_url": f"https://x/{cid}"})
    c.user.login = login
    return c


def test_existing_bot_comment_is_edited_instead_of_creating_a_new_one():
    human = _comment("mallory", f"{MARKER}\nfake review", 1)
    ours = _comment("ignition-review[bot]", f"{MARKER}\nold review", 2)
    gh, issue = _client_with_comments([human, ours])
    result = gh.upsert_sticky_comment("acme/widgets", 7, "new review", bot_login="ignition-review[bot]")
    ours.edit.assert_called_once_with(f"{MARKER}\nnew review")
    human.edit.assert_not_called()
    issue.create_comment.assert_not_called()
    assert result["id"] == 2


def test_comment_is_created_when_the_bot_has_none_yet():
    human = _comment("mallory", f"{MARKER}\nfake review", 1)
    gh, issue = _client_with_comments([human])
    gh.upsert_sticky_comment("acme/widgets", 7, "first review", bot_login="ignition-review[bot]")
    issue.create_comment.assert_called_once_with(f"{MARKER}\nfirst review")
    human.edit.assert_not_called()


def test_bot_login_comes_from_the_configured_app_slug(monkeypatch):
    monkeypatch.setenv("GITHUB_APP_SLUG", "ignition-review")
    github_client_module._app_slug.cache_clear()
    from app.config import get_settings
    get_settings.cache_clear()
    try:
        assert GitHubClient.__new__(GitHubClient).bot_login == "ignition-review[bot]"
    finally:
        get_settings.cache_clear()
        github_client_module._app_slug.cache_clear()


def _signed(body: bytes) -> str:
    import hashlib
    import hmac
    from app.config import get_settings
    return "sha256=" + hmac.new(get_settings().github_webhook_secret.encode(), body, hashlib.sha256).hexdigest()


def _pr_event(action="opened", draft=False):
    return {
        "action": action,
        "repository": {"id": 1001, "full_name": "acme/widgets", "default_branch": "main",
                       "clone_url": "https://github.com/acme/widgets.git"},
        "pull_request": {"number": 7, "draft": draft, "diff_url": "https://github.com/acme/widgets/pull/7.diff",
                         "head": {"sha": "a" * 40}, "base": {"sha": "b" * 40}},
        "installation": {"id": 999},
    }


async def _post_webhook(payload, monkeypatch):
    pool = AsyncMock()
    pool.enqueue_job = AsyncMock(return_value=MagicMock(job_id="job"))

    async def get_pool():
        return pool

    monkeypatch.setattr(main_module, "get_arq_pool", get_pool)
    monkeypatch.setattr(main_module.repo_repo, "get_or_create_repo", lambda name, github_repo_id=None: {"id": name})
    monkeypatch.setattr(main_module.review_repo, "create_review", lambda **kw: kw)
    monkeypatch.setattr(main_module.review_repo, "update_review", lambda rid, upd: upd)
    body = json.dumps(payload).encode()
    transport = httpx.ASGITransport(app=main_module.app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post("/webhooks/github", content=body, headers={
            "Content-Type": "application/json", "X-Hub-Signature-256": _signed(body),
            "X-GitHub-Delivery": f"d-{payload['action']}-{payload['pull_request']['draft']}"})
    return res, pool


@pytest.mark.asyncio
async def test_draft_pull_requests_are_skipped(monkeypatch):
    res, pool = await _post_webhook(_pr_event("opened", draft=True), monkeypatch)
    assert res.status_code == 202 and res.json()["status"] == "ignored"
    pool.enqueue_job.assert_not_awaited()


@pytest.mark.asyncio
async def test_ready_for_review_enqueues_with_a_per_sha_job_id(monkeypatch):
    res, pool = await _post_webhook(_pr_event("ready_for_review"), monkeypatch)
    assert res.status_code == 202 and res.json()["status"] == "queued"
    assert pool.enqueue_job.await_args.kwargs["_job_id"] == f"review:acme/widgets:7:{'a' * 40}"
