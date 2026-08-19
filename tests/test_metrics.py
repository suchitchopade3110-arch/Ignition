"""
GET /metrics (app/main.py, app/services/metrics.py) — Prometheus scrape
target added after the deployment-readiness review flagged the app as
having no metrics/observability beyond structured logs.
"""
from unittest.mock import patch

import httpx
import pytest

import app.main as main_module
from app.config import get_settings


@pytest.mark.asyncio
async def test_metrics_endpoint_returns_prometheus_text_format():
    transport = httpx.ASGITransport(app=main_module.app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/metrics")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")
    # A couple of the metrics this module defines should always be present
    # in the exposition text, even with a value of 0 — Counters/Histograms/
    # Gauges are registered at import time (app/services/metrics.py), not
    # lazily on first use.
    assert "ignition_http_requests_total" in response.text
    assert "ignition_webhook_events_total" in response.text
    assert "ignition_reviews_completed_total" in response.text
    assert "ignition_hitl_resolutions_total" in response.text


@pytest.mark.asyncio
async def test_metrics_endpoint_reflects_recorded_requests():
    """The HTTP metrics middleware (app/main.py::_record_http_metrics)
    should have already counted THIS test's own prior requests by the time
    /metrics is scraped — labeled by route template, not raw path."""
    transport = httpx.ASGITransport(app=main_module.app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        await client.get("/healthz")  # any cheap, unauthenticated route
        response = await client.get("/metrics")

    assert 'path="/healthz"' in response.text


@pytest.mark.asyncio
async def test_metrics_endpoint_disabled_returns_404():
    settings = get_settings()
    with patch.object(settings, "metrics_enabled", False):
        transport = httpx.ASGITransport(app=main_module.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/metrics")
    assert response.status_code == 404
