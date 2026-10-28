"""
P2 "misleading output" (wired with audit P1-4): the review page's preview
panel showed a GitHub comment URL (only after a HITL approval) instead of
what Ignition posts. The review API now returns final_comment_markdown for
every review, and the panel renders it with react-markdown.
"""
import httpx
import pytest

import app.main as main_module
from app.auth import AuthUser, get_current_user, require_review_repo_access
from app.services.review_pipeline import review_repo
from tests.fake_supabase import FakeSupabase


@pytest.mark.asyncio
async def test_review_detail_returns_the_final_comment_markdown(monkeypatch):
    db = FakeSupabase({"reviews": [{
        "id": "r-1", "repo_full_name": "acme/widgets", "pr_number": 7, "title": "PR", "status": "completed",
        "created_at": "2026-10-27T00:00:00+00:00", "final_comment_markdown": "## Ignition Review — ACS: 90.0",
    }]})
    monkeypatch.setattr(review_repo, "_db", db)
    user = AuthUser(id="u", github_id=1, login="octocat")
    main_module.app.dependency_overrides[get_current_user] = lambda: user
    main_module.app.dependency_overrides[require_review_repo_access] = lambda: user
    try:
        transport = httpx.ASGITransport(app=main_module.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            res = await client.get("/api/reviews/r-1")
    finally:
        main_module.app.dependency_overrides.clear()
    assert res.status_code == 200
    assert res.json()["finalCommentMarkdown"] == "## Ignition Review — ACS: 90.0"
