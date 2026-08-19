"""
Coverage for /api/hitl/{review_id}/approve, /reject, and
/api/reviews/{review_id}/stream — previously untested despite being real
API surface (the human-in-the-loop resolution path, and the SSE endpoint
the whole live-progress dashboard depends on).

Auth is bypassed via FastAPI's dependency_overrides rather than exercising
the real GitHub-OAuth-backed check_repo_access — that path is already
covered directly in tests/test_auth_access.py; these tests are about what
each route does once past auth, not auth itself.
"""
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

import app.main as main_module
from app.auth import AuthUser, get_current_user, require_review_repo_access
from app.services.review_pipeline import review_repo
from app.services.stream_manager import stream_manager

_FAKE_USER = AuthUser(id="u1", github_id=1, login="octocat")


@pytest.fixture
def override_auth():
    main_module.app.dependency_overrides[get_current_user] = lambda: _FAKE_USER
    main_module.app.dependency_overrides[require_review_repo_access] = lambda: _FAKE_USER
    yield
    main_module.app.dependency_overrides.pop(get_current_user, None)
    main_module.app.dependency_overrides.pop(require_review_repo_access, None)


@pytest.fixture
def fake_review(monkeypatch):
    """A single review row plus the minimal review_repo surface the HITL
    routes touch, faked the same way as
    test_integration_webhook_review_comment.FakeReviewRepo."""
    rows = {
        "review-1": {
            "id": "review-1",
            "status": "waiting_hitl",
            "repo_full_name": "acme/widgets",
            "installation_id": 999,
            "pr_number": 7,
            "final_comment_markdown": "## Review\nLooks fine.",
            "correlation_id": "corr-1",
        }
    }

    def get_review(review_id):
        return rows.get(review_id)

    def get_review_github_context(review_id):
        row = rows.get(review_id)
        if not row:
            return None
        return {k: row.get(k) for k in
                ("repo_full_name", "installation_id", "pr_number", "final_comment_markdown", "correlation_id")}

    def update_review(review_id, updates):
        rows.setdefault(review_id, {}).update(updates)
        return rows[review_id]

    monkeypatch.setattr(review_repo, "get_review", get_review)
    monkeypatch.setattr(review_repo, "get_review_github_context", get_review_github_context)
    monkeypatch.setattr(review_repo, "update_review", update_review)
    return rows


@pytest.mark.asyncio
async def test_approve_hitl_posts_comment_and_publishes_events(override_auth, fake_review):
    mock_gh_instance = MagicMock()
    mock_gh_instance.post_review_comment.return_value = {
        "id": 123, "html_url": "https://github.com/acme/widgets/pull/7#issuecomment-123",
    }
    with patch("app.services.github_client.GitHubClient", return_value=mock_gh_instance), \
         patch.object(stream_manager, "publish", new=AsyncMock()) as mock_publish:
        transport = httpx.ASGITransport(app=main_module.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post("/api/hitl/review-1/approve")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["github_comment_url"].endswith("issuecomment-123")
    assert fake_review["review-1"]["status"] == "completed"
    mock_gh_instance.post_review_comment.assert_called_once()
    published_types = [call.args[1]["type"] for call in mock_publish.await_args_list]
    assert "hitl.approved" in published_types
    assert "review.completed" in published_types


@pytest.mark.asyncio
async def test_approve_hitl_surfaces_github_post_failure_as_502(override_auth, fake_review):
    """A failed GitHub post must not be swallowed into a false success —
    this is the exact failure mode app/main.py's own docstring calls out."""
    mock_gh_instance = MagicMock()
    mock_gh_instance.post_review_comment.side_effect = RuntimeError("GitHub API unreachable")
    with patch("app.services.github_client.GitHubClient", return_value=mock_gh_instance):
        transport = httpx.ASGITransport(app=main_module.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post("/api/hitl/review-1/approve")

    assert response.status_code == 502
    # The comment preview URL must never be recorded when the post itself
    # failed — that's the "silently returning success" failure mode the
    # route's own docstring calls out.
    assert "github_comment_preview" not in fake_review["review-1"]


@pytest.mark.asyncio
async def test_approve_hitl_missing_review_is_404(override_auth, fake_review):
    transport = httpx.ASGITransport(app=main_module.app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/hitl/does-not-exist/approve")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_reject_hitl_publishes_rejected_events(override_auth, fake_review):
    with patch.object(stream_manager, "publish", new=AsyncMock()) as mock_publish:
        transport = httpx.ASGITransport(app=main_module.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post("/api/hitl/review-1/reject")

    assert response.status_code == 200
    assert response.json() == {"success": True}
    assert fake_review["review-1"]["status"] == "completed"
    published_types = [call.args[1]["type"] for call in mock_publish.await_args_list]
    assert "hitl.rejected" in published_types
    assert "review.completed" in published_types


@pytest.mark.asyncio
async def test_stream_endpoint_emits_named_sse_events(override_auth, fake_review):
    """Regression coverage for the bug called out in main.py's own
    docstring: events must be sent as named `event: <type>` SSE frames
    (frontend listens via addEventListener), not bare `data:` lines."""
    async def fake_stream(review_id):
        yield {"type": "review.started", "reviewId": review_id}
        yield {"type": "review.completed", "reviewId": review_id, "status": "completed"}

    with patch.object(stream_manager, "stream", new=fake_stream):
        transport = httpx.ASGITransport(app=main_module.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            async with client.stream("GET", "/api/reviews/review-1/stream") as response:
                assert response.status_code == 200
                assert response.headers["content-type"].startswith("text/event-stream")
                body = ""
                async for chunk in response.aiter_text():
                    body += chunk

    assert "event: review.started" in body
    assert "event: review.completed" in body
    assert '"reviewId":"review-1"' in body or '"reviewId": "review-1"' in body


@pytest.mark.asyncio
async def test_stream_endpoint_requires_auth():
    """No dependency override here — the real require_review_repo_access
    (and therefore get_current_user) must reject an unauthenticated call."""
    transport = httpx.ASGITransport(app=main_module.app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/reviews/review-1/stream")
    assert response.status_code == 401
