"""
I-5: /healthz was the platform probe and hit Groq and Supabase on every
poll. Now:
  - GET /livez -> {"status": "ok"}, no dependencies: Render's health check;
  - the deep check is GET /readyz, behind Authorization: Bearer
    $READYZ_TOKEN, cached for 15 s, and its errors name only the exception
    class (never str(e), which can carry URLs or keys).
"""
from pathlib import Path
from unittest.mock import AsyncMock, patch

import httpx
import pytest
import yaml

import app.main as main_module
from app.config import get_settings
from app.services import health_checks

TOKEN = "readyz-test-token"
REPO = Path(__file__).resolve().parents[1]


async def _get(path, token=None):
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    transport = httpx.ASGITransport(app=main_module.app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        return await client.get(path, headers=headers)


@pytest.fixture
def deep(monkeypatch):
    checks = AsyncMock(return_value=({"status": "healthy", "checks": {}}, True))
    monkeypatch.setattr(main_module, "run_health_checks", checks, raising=False)
    monkeypatch.setattr(health_checks, "run_health_checks", checks)
    monkeypatch.setitem(get_settings().__dict__, "readyz_token", TOKEN)
    getattr(main_module, "_readyz_cache", {}).clear()
    yield checks
    getattr(main_module, "_readyz_cache", {}).clear()


@pytest.mark.asyncio
async def test_livez_touches_no_dependency(deep):
    res = await _get("/livez")
    assert res.status_code == 200 and res.json() == {"status": "ok"}
    deep.assert_not_awaited()


@pytest.mark.asyncio
async def test_readyz_requires_the_bearer_token(deep):
    assert (await _get("/readyz")).status_code == 401
    assert (await _get("/readyz", token="wrong")).status_code == 401
    deep.assert_not_awaited()
    res = await _get("/readyz", token=TOKEN)
    assert res.status_code == 200 and res.json()["status"] == "healthy"


@pytest.mark.asyncio
async def test_readyz_is_cached_for_15_seconds(deep, monkeypatch):
    clock = {"now": 1000.0}
    monkeypatch.setattr(main_module.time, "monotonic", lambda: clock["now"])
    await _get("/readyz", token=TOKEN)
    clock["now"] += 14
    await _get("/readyz", token=TOKEN)
    assert deep.await_count == 1
    clock["now"] += 2
    await _get("/readyz", token=TOKEN)
    assert deep.await_count == 2


@pytest.mark.asyncio
async def test_unhealthy_readyz_is_a_503(deep):
    deep.return_value = ({"status": "unhealthy", "checks": {}}, False)
    assert (await _get("/readyz", token=TOKEN)).status_code == 503


@pytest.mark.asyncio
async def test_readyz_without_a_configured_token(deep, monkeypatch):
    monkeypatch.setitem(get_settings().__dict__, "readyz_token", "")
    monkeypatch.setattr(get_settings(), "app_env", "production")
    assert (await _get("/readyz")).status_code == 404  # fail closed in production
    monkeypatch.setattr(get_settings(), "app_env", "development")
    assert (await _get("/readyz")).status_code == 200  # open locally


@pytest.mark.asyncio
async def test_the_old_healthz_route_is_gone(deep):
    assert (await _get("/healthz")).status_code == 404


@pytest.mark.asyncio
async def test_check_errors_name_only_the_exception_class(monkeypatch):
    def boom():
        raise RuntimeError("could not connect to https://secret-project.supabase.co?apikey=sk-live-123")
    monkeypatch.setattr(health_checks, "get_supabase", boom)
    result = await health_checks.check_supabase()
    assert result["status"] == "unhealthy" and result["error"] == "RuntimeError"


def test_render_probes_livez_and_has_a_readyz_token():
    services = {s["name"]: s for s in yaml.safe_load((REPO / "render.yaml").read_text())["services"]}
    backend = services["ignition-backend"]
    assert backend["healthCheckPath"] == "/livez"
    assert {"key": "READYZ_TOKEN", "sync": False} in backend["envVars"]
