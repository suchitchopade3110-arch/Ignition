"""
app.security.verify_csrf_token — the double-submit-cookie CSRF check added
to /api/hitl/{id}/approve, /reject, and PATCH /api/repos/{id}/settings.
"""
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException, Request

from app.config import get_settings
from app.security import verify_csrf_token


def _request(cookies: dict | None = None, headers: dict | None = None) -> Request:
    req = MagicMock(spec=Request)
    req.cookies = cookies or {}
    req.headers = headers or {}
    return req


@pytest.mark.asyncio
async def test_matching_cookie_and_header_passes():
    settings = get_settings()
    token = "matching-token-value"
    req = _request(
        cookies={settings.csrf_cookie_name: token},
        headers={settings.csrf_header_name: token},
    )
    await verify_csrf_token(req)  # does not raise


@pytest.mark.asyncio
async def test_missing_cookie_is_rejected():
    settings = get_settings()
    req = _request(headers={settings.csrf_header_name: "some-token"})
    with pytest.raises(HTTPException) as exc_info:
        await verify_csrf_token(req)
    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_missing_header_is_rejected():
    settings = get_settings()
    req = _request(cookies={settings.csrf_cookie_name: "some-token"})
    with pytest.raises(HTTPException) as exc_info:
        await verify_csrf_token(req)
    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_mismatched_cookie_and_header_is_rejected():
    """The exact attack this check exists to stop: an attacker's page can
    trigger a cross-site request that carries the victim's session cookie,
    but cannot read that cookie's value to also set a matching header."""
    settings = get_settings()
    req = _request(
        cookies={settings.csrf_cookie_name: "real-token-from-cookie"},
        headers={settings.csrf_header_name: "attacker-guessed-token"},
    )
    with pytest.raises(HTTPException) as exc_info:
        await verify_csrf_token(req)
    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_empty_string_token_is_rejected():
    """An empty cookie/header pair must not trivially "match" each other."""
    settings = get_settings()
    req = _request(
        cookies={settings.csrf_cookie_name: ""},
        headers={settings.csrf_header_name: ""},
    )
    with pytest.raises(HTTPException) as exc_info:
        await verify_csrf_token(req)
    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_hitl_approve_rejects_missing_csrf_header(monkeypatch):
    """End-to-end: the route itself 403s without a matching CSRF header,
    even with a valid session — not just the unit-level dependency."""
    import httpx
    import app.main as main_module
    from app.auth import AuthUser, get_current_user, require_review_repo_access

    main_module.app.dependency_overrides[get_current_user] = lambda: AuthUser(
        id="u1", github_id=1, login="octocat"
    )
    main_module.app.dependency_overrides[require_review_repo_access] = lambda: AuthUser(
        id="u1", github_id=1, login="octocat"
    )
    try:
        transport = httpx.ASGITransport(app=main_module.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post("/api/hitl/some-review/approve")
        assert response.status_code == 403
    finally:
        main_module.app.dependency_overrides.pop(get_current_user, None)
        main_module.app.dependency_overrides.pop(require_review_repo_access, None)
