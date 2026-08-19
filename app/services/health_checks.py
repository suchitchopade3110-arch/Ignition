"""
Real dependency reachability checks for /healthz (app/main.py). Three
explicit checks, each with its own timeout — not a health-check framework,
just plain async functions gathered together.
"""
import asyncio
import time

import httpx

from app.config import get_settings
from app.database import get_supabase
from app.services.llm_client import get_llm_client
from app.services.redis_client import get_pubsub_redis

_CHECK_TIMEOUT_SECONDS = 3.0


def _result(status: str, latency_ms: int, error: str | None = None) -> dict:
    payload = {"status": status, "latency_ms": latency_ms}
    if error:
        payload["error"] = error
    return payload


async def check_supabase() -> dict:
    """A real round-trip query, not just 'can I open a connection' — the
    Supabase client is synchronous (httpx under the hood), so it's run in
    a thread so asyncio.wait_for's timeout can actually apply to it."""
    start = time.monotonic()

    def _query():
        db = get_supabase()
        db.table("reviews").select("id").limit(1).execute()

    try:
        await asyncio.wait_for(asyncio.to_thread(_query), timeout=_CHECK_TIMEOUT_SECONDS)
        return _result("healthy", int((time.monotonic() - start) * 1000))
    except asyncio.TimeoutError:
        return _result("unhealthy", int((time.monotonic() - start) * 1000), "timed out")
    except Exception as e:
        return _result("unhealthy", int((time.monotonic() - start) * 1000), str(e))


async def check_ast_analyzer() -> dict:
    """Hits the analyzer's own /healthz — a request FROM inside the
    network boundary set up in Phase 1 (this FastAPI/worker process is
    exactly the caller that boundary was built to allow), not a new hole
    in it."""
    settings = get_settings()
    start = time.monotonic()
    try:
        async with httpx.AsyncClient(timeout=_CHECK_TIMEOUT_SECONDS) as client:
            response = await client.get(f"{settings.ast_service_url}/healthz")
        if response.status_code == 200:
            return _result("healthy", int((time.monotonic() - start) * 1000))
        return _result(
            "unhealthy", int((time.monotonic() - start) * 1000), f"HTTP {response.status_code}"
        )
    except Exception as e:
        return _result("unhealthy", int((time.monotonic() - start) * 1000), str(e))


async def check_llm_provider() -> dict:
    """A models-list call, not a completion — cheapest real reachability
    check Groq's API offers; doesn't burn tokens or cost on every poll.
    Uses the shared LLMClient's underlying AsyncGroq (get_llm_client) —
    not a second instance just for health checks."""
    start = time.monotonic()
    try:
        client = get_llm_client().raw_client
        await asyncio.wait_for(client.models.list(), timeout=_CHECK_TIMEOUT_SECONDS)
        return _result("healthy", int((time.monotonic() - start) * 1000))
    except asyncio.TimeoutError:
        return _result("unhealthy", int((time.monotonic() - start) * 1000), "timed out")
    except Exception as e:
        return _result("unhealthy", int((time.monotonic() - start) * 1000), str(e))


async def check_redis() -> dict:
    """Was missing entirely — the app is fully dependent on Redis (the Arq
    job queue AND the SSE pub/sub backbone in stream_manager.py), so a
    "healthy" /healthz that never actually checked it could report green
    while every webhook enqueue and every live SSE stream was silently
    broken. Uses the same shared pub/sub client the rest of the app uses
    (app/services/redis_client.py::get_pubsub_redis) rather than opening a
    dedicated connection just for this check."""
    start = time.monotonic()
    try:
        client = get_pubsub_redis()
        await asyncio.wait_for(client.ping(), timeout=_CHECK_TIMEOUT_SECONDS)
        return _result("healthy", int((time.monotonic() - start) * 1000))
    except asyncio.TimeoutError:
        return _result("unhealthy", int((time.monotonic() - start) * 1000), "timed out")
    except Exception as e:
        return _result("unhealthy", int((time.monotonic() - start) * 1000), str(e))


async def run_health_checks() -> tuple[dict, bool]:
    """Returns (response_body, all_healthy)."""
    supabase, ast_analyzer, llm_provider, redis = await asyncio.gather(
        check_supabase(), check_ast_analyzer(), check_llm_provider(), check_redis()
    )
    checks = {
        "supabase": supabase,
        "ast_analyzer": ast_analyzer,
        "llm_provider": llm_provider,
        "redis": redis,
    }
    all_healthy = all(c["status"] == "healthy" for c in checks.values())
    return {"status": "healthy" if all_healthy else "unhealthy", "checks": checks}, all_healthy
