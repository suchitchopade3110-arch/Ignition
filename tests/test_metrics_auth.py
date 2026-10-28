"""
I-11: /metrics was public. It now requires Authorization: Bearer
$METRICS_TOKEN (compared with hmac.compare_digest); with no token
configured it is 404 in production (and open in development, for local
scraping). METRICS_ENABLED=false still turns it off entirely.
"""
from pathlib import Path

import httpx
import pytest
import yaml

import app.main as main_module
from app.config import get_settings

TOKEN = "metrics-test-token"
REPO = Path(__file__).resolve().parents[1]


async def _get(token=None):
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    transport = httpx.ASGITransport(app=main_module.app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        return await client.get("/metrics", headers=headers)


@pytest.mark.asyncio
async def test_a_configured_token_is_required(monkeypatch):
    monkeypatch.setitem(get_settings().__dict__, "metrics_token", TOKEN)
    assert (await _get()).status_code == 401
    assert (await _get("wrong")).status_code == 401
    res = await _get(TOKEN)
    assert res.status_code == 200 and "ignition_http_requests_total" in res.text


@pytest.mark.asyncio
async def test_no_token_in_production_hides_the_endpoint(monkeypatch):
    monkeypatch.setitem(get_settings().__dict__, "metrics_token", "")
    monkeypatch.setattr(get_settings(), "app_env", "production")
    assert (await _get()).status_code == 404


@pytest.mark.asyncio
async def test_no_token_in_development_stays_open_for_local_scraping(monkeypatch):
    monkeypatch.setitem(get_settings().__dict__, "metrics_token", "")
    monkeypatch.setattr(get_settings(), "app_env", "development")
    assert (await _get()).status_code == 200


def test_the_token_comparison_is_constant_time():
    import inspect
    assert "hmac.compare_digest" in inspect.getsource(main_module.metrics_endpoint)


def test_render_declares_a_metrics_token():
    services = {s["name"]: s for s in yaml.safe_load((REPO / "render.yaml").read_text())["services"]}
    assert {"key": "METRICS_TOKEN", "sync": False} in services["ignition-backend"]["envVars"]
