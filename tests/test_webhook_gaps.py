"""
Coverage for three gaps fixed after the endpoint/deployment-readiness
review: (1) author/branch were hardcoded rather than read off the webhook
payload, (2) non-`pull_request` GitHub events (ping, installation,
installation_repositories) used to fall through to PullRequestWebhook
validation and 422, (3) /healthz never actually checked Redis reachability.

Reuses the FakeReviewRepo/FakeRepoRepo/mock fixtures from
test_integration_webhook_review_comment.py rather than redefining them —
same fakes, same mocking rationale (see that module's docstring).
"""
import hashlib
import hmac
import json
from unittest.mock import AsyncMock, patch

import httpx
import pytest

import app.main as main_module
from app.config import get_settings
from app.services import health_checks
from tests.test_integration_webhook_review_comment import (
    fake_repos,  # noqa: F401 — fixture re-export
    mock_externals,  # noqa: F401
    mock_arq,  # noqa: F401
    _webhook_payload,
)


def _sign(body: bytes) -> str:
    secret = get_settings().github_webhook_secret
    return "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


@pytest.mark.asyncio
async def test_webhook_uses_real_author_and_branch(fake_repos, mock_externals, mock_arq):  # noqa: F811
    """author/branch used to be hardcoded to "unknown"/"main" regardless of
    what the payload actually said — this asserts they now come from
    pull_request.user.login / pull_request.head.ref."""
    fake_review_repo, _ = fake_repos
    payload = _webhook_payload()
    payload["pull_request"]["user"] = {"login": "octocat"}
    payload["pull_request"]["head"]["ref"] = "feature/real-branch"
    body = json.dumps(payload).encode()
    signature = _sign(body)

    transport = httpx.ASGITransport(app=main_module.app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/webhooks/github", content=body,
            headers={"Content-Type": "application/json", "X-Hub-Signature-256": signature,
                     "X-GitHub-Delivery": "author-branch-test", "X-GitHub-Event": "pull_request"},
        )

    assert response.status_code == 202
    review_id = response.json()["reviewId"]
    row = fake_review_repo.rows[review_id]
    assert row["author"] == "octocat"
    assert row["branch"] == "feature/real-branch"


@pytest.mark.asyncio
async def test_webhook_missing_user_falls_back_to_unknown(fake_repos, mock_externals, mock_arq):  # noqa: F811
    """A payload that genuinely omits `user` (schema field is optional)
    still degrades gracefully instead of failing validation."""
    fake_review_repo, _ = fake_repos
    payload = _webhook_payload()  # no user, no head.ref
    body = json.dumps(payload).encode()
    signature = _sign(body)

    transport = httpx.ASGITransport(app=main_module.app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/webhooks/github", content=body,
            headers={"Content-Type": "application/json", "X-Hub-Signature-256": signature,
                     "X-GitHub-Delivery": "fallback-test"},
        )

    assert response.status_code == 202
    review_id = response.json()["reviewId"]
    row = fake_review_repo.rows[review_id]
    assert row["author"] == "unknown"
    assert row["branch"] == "unknown"


@pytest.mark.asyncio
async def test_webhook_ping_event_acknowledged_without_processing():
    body = json.dumps({"zen": "Responsive is better than fast.", "hook_id": 1}).encode()
    signature = _sign(body)

    transport = httpx.ASGITransport(app=main_module.app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/webhooks/github", content=body,
            headers={"Content-Type": "application/json", "X-Hub-Signature-256": signature,
                     "X-GitHub-Delivery": "ping-test", "X-GitHub-Event": "ping"},
        )

    assert response.status_code == 202
    assert response.json() == {"status": "pong"}


@pytest.mark.asyncio
async def test_webhook_installation_event_processed_not_rejected():
    """Previously this event type would hit PullRequestWebhook.model_validate
    and 422 — it's a real GitHub event, not a malformed payload. Actual
    register/deregister behavior is covered in tests/test_installation_webhook.py;
    this just asserts the webhook route itself doesn't 422 on it."""
    body = json.dumps({"action": "created", "installation": {"id": 42}}).encode()
    signature = _sign(body)

    transport = httpx.ASGITransport(app=main_module.app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/webhooks/github", content=body,
            headers={"Content-Type": "application/json", "X-Hub-Signature-256": signature,
                     "X-GitHub-Delivery": "install-test", "X-GitHub-Event": "installation"},
        )

    assert response.status_code == 202
    assert response.json() == {"status": "processed", "event": "installation"}


@pytest.mark.asyncio
async def test_webhook_unactionable_event_type_ignored():
    """An event type this app has no handling for at all (e.g. `issues`)
    is acknowledged, not rejected."""
    body = json.dumps({"action": "opened"}).encode()
    signature = _sign(body)

    transport = httpx.ASGITransport(app=main_module.app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/webhooks/github", content=body,
            headers={"Content-Type": "application/json", "X-Hub-Signature-256": signature,
                     "X-GitHub-Delivery": "issues-test", "X-GitHub-Event": "issues"},
        )

    assert response.status_code == 202
    assert response.json() == {"status": "ignored", "event": "issues"}


@pytest.mark.asyncio
async def test_healthz_reports_redis_check():
    """/healthz previously checked Supabase, the AST analyzer, and the LLM
    provider but never Redis — despite the app being fully dependent on it
    for the Arq queue and SSE pub/sub."""
    with patch.object(health_checks, "check_supabase", new=AsyncMock(return_value={"status": "healthy", "latency_ms": 1})), \
         patch.object(health_checks, "check_ast_analyzer", new=AsyncMock(return_value={"status": "healthy", "latency_ms": 1})), \
         patch.object(health_checks, "check_llm_provider", new=AsyncMock(return_value={"status": "healthy", "latency_ms": 1})), \
         patch.object(health_checks, "check_redis", new=AsyncMock(return_value={"status": "unhealthy", "latency_ms": 1, "error": "connection refused"})):
        body, all_healthy = await health_checks.run_health_checks()

    assert "redis" in body["checks"]
    assert body["checks"]["redis"]["status"] == "unhealthy"
    assert all_healthy is False
    assert body["status"] == "unhealthy"
