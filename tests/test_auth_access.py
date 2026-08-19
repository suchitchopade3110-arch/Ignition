"""
app.auth.check_repo_access — the per-repo authorization dependency gating
every /api/repos/{...} and /api/reviews/{review_id} route. Previously
untested despite being the actual access-control boundary for the whole
dashboard API.
"""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException, Request

from app.auth import check_repo_access


def _request_with_token(token: str = "gh-token") -> Request:
    req = MagicMock(spec=Request)
    req.state = MagicMock()
    req.state.github_access_token = token
    return req


def _mock_httpx_response(status_code: int, json_body: dict | None = None):
    response = MagicMock()
    response.status_code = status_code
    response.json.return_value = json_body or {}
    return response


@pytest.mark.asyncio
async def test_no_token_raises_401():
    req = MagicMock(spec=Request)
    req.state = MagicMock(spec=[])  # no github_access_token attribute at all
    with pytest.raises(HTTPException) as exc_info:
        await check_repo_access(req, "acme/widgets")
    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_push_permission_grants_access():
    req = _request_with_token()
    response = _mock_httpx_response(200, {"permissions": {"push": True, "admin": False}})
    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("httpx.AsyncClient", return_value=mock_client):
        await check_repo_access(req, "acme/widgets")  # does not raise


@pytest.mark.asyncio
async def test_read_only_access_is_forbidden():
    """A 200 with no push/admin/maintain permission — e.g. any authenticated
    user reading a public repo's metadata — must NOT count as access."""
    req = _request_with_token()
    response = _mock_httpx_response(200, {"permissions": {"pull": True, "push": False, "admin": False}})
    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("httpx.AsyncClient", return_value=mock_client):
        with pytest.raises(HTTPException) as exc_info:
            await check_repo_access(req, "acme/widgets")
    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_repo_not_found_is_forbidden_not_404():
    """404 from GitHub (repo doesn't exist, or exists but caller can't see
    it at all) is deliberately surfaced as 403, not 404 — doesn't leak
    whether a private repo exists."""
    req = _request_with_token()
    response = _mock_httpx_response(404)
    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("httpx.AsyncClient", return_value=mock_client):
        with pytest.raises(HTTPException) as exc_info:
            await check_repo_access(req, "acme/private-widgets")
    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_unexpected_github_status_is_502():
    req = _request_with_token()
    response = _mock_httpx_response(500)
    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("httpx.AsyncClient", return_value=mock_client):
        with pytest.raises(HTTPException) as exc_info:
            await check_repo_access(req, "acme/widgets")
    assert exc_info.value.status_code == 502
