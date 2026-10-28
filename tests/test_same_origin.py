"""
Audit P0-5: the API is served through the frontend's own origin (Next.js
rewrites). The blueprint must wire that topology end to end, and the SSE
stream must tell any proxy not to buffer it.
"""
from pathlib import Path

import httpx
import pytest
import yaml

import app.main as main_module
from app.auth import AuthUser, get_current_user, require_review_repo_access

REPO_ROOT = Path(__file__).resolve().parents[1]


def _env(service: dict) -> dict:
    return {e["key"]: e.get("value") for e in service.get("envVars", []) if "key" in e}


def test_blueprint_wires_the_same_origin_topology():
    services = {s["name"]: s for s in yaml.safe_load((REPO_ROOT / "render.yaml").read_text())["services"]}
    backend, frontend = _env(services["ignition-backend"]), _env(services["ignition-frontend"])
    assert backend["SESSION_COOKIE_SAMESITE"] == "lax"
    # OAuth redirect_uri is built from BACKEND_BASE_URL: it must be the
    # frontend origin so the session cookie is set there.
    assert backend["BACKEND_BASE_URL"] == backend["FRONTEND_BASE_URL"] == "https://ignition-frontend.onrender.com"
    assert frontend["NEXT_PUBLIC_API_URL"] == "/api"
    assert frontend["NEXT_PUBLIC_BACKEND_URL"] == ""
    assert frontend["BACKEND_INTERNAL_URL"] == "https://ignition-backend.onrender.com"


@pytest.mark.asyncio
async def test_sse_stream_disables_proxy_buffering(monkeypatch):
    user = AuthUser(id="u", github_id=1, login="u")
    main_module.app.dependency_overrides[get_current_user] = lambda: user
    main_module.app.dependency_overrides[require_review_repo_access] = lambda: user
    monkeypatch.setattr(main_module.review_repo, "get_review_github_context", lambda review_id: None)

    async def one_event(review_id):
        yield {"type": "review.completed", "reviewId": review_id, "status": "completed"}

    monkeypatch.setattr(main_module.stream_manager, "stream", one_event)
    try:
        transport = httpx.ASGITransport(app=main_module.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            res = await client.get("/api/reviews/r1/stream")
    finally:
        main_module.app.dependency_overrides.clear()
    assert res.status_code == 200
    assert res.headers["x-accel-buffering"] == "no"
    assert "event: review.completed" in res.text


@pytest.mark.asyncio
async def test_sse_stream_flushes_a_comment_before_the_first_event(monkeypatch):
    # The Next.js rewrite holds the response headers until the first body
    # byte arrives; an immediate SSE comment lets the browser's EventSource
    # open at once instead of waiting for the first real event.
    user = AuthUser(id="u", github_id=1, login="u")
    main_module.app.dependency_overrides[get_current_user] = lambda: user
    main_module.app.dependency_overrides[require_review_repo_access] = lambda: user
    monkeypatch.setattr(main_module.review_repo, "get_review_github_context", lambda review_id: None)

    async def one_event(review_id):
        yield {"type": "review.completed", "reviewId": review_id, "status": "completed"}

    monkeypatch.setattr(main_module.stream_manager, "stream", one_event)
    try:
        transport = httpx.ASGITransport(app=main_module.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            res = await client.get("/api/reviews/r1/stream")
    finally:
        main_module.app.dependency_overrides.clear()
    assert res.text.startswith(": connected\n\n")
