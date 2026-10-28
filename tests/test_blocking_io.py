"""
Audit P1-7 (step 1): blocking I/O on the event loop. Supabase and PyGithub
are synchronous clients; called directly from async code they freeze the
loop, so two reviews on one worker run one after the other and the
review's asyncio.wait_for budget can't fire while a call is stuck.

Step 1: Supabase-only routes are plain `def` (FastAPI runs them in its
thread pool); in async code (the worker job, the Critic, the webhook,
approve/reject, auth) those calls go through asyncio.to_thread. Step 2
(the async Supabase client) is deferred by the doc.
"""
import asyncio
import inspect
import json
import time
from unittest.mock import patch

import httpx
import pytest

import app.main as main_module
import app.services.review_pipeline as pipeline
from app.repositories.ledger import LedgerRepository
from app.services.review_pipeline import run_review_job
from tests.test_integration_webhook_review_comment import (  # noqa: F401  (fixtures)
    _sign, _webhook_payload, fake_repos, mock_arq, mock_externals,
)

BLOCK_SECONDS = 0.6
BUDGET_SECONDS = 0.3


def _slow_baseline(self, repo_full_name):
    time.sleep(BLOCK_SECONDS)  # a synchronous Supabase round trip
    return None


async def _slow_llm(self, prompt, json_mode=True, agent_name="unknown"):
    await asyncio.sleep(5)  # a slowed provider (async: never blocked the loop)
    return '{"findings": []}'


@pytest.mark.asyncio
@pytest.mark.parametrize("slow", ["supabase", "llm"])
async def test_two_reviews_progress_together_and_the_budget_fires_on_time(slow, fake_repos, mock_externals, mock_arq):
    fake_review_repo, _ = fake_repos
    jobs = []
    for delivery in ("one", "two"):
        mock_arq.enqueue_job.reset_mock()
        payload = _webhook_payload()
        payload["pull_request"]["number"] = 7 if delivery == "one" else 8
        body = json.dumps(payload).encode()
        transport = httpx.ASGITransport(app=main_module.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            res = await client.post("/webhooks/github", content=body, headers={
                "Content-Type": "application/json", "X-Hub-Signature-256": _sign(body),
                "X-GitHub-Delivery": f"blocking-{delivery}"})
        assert res.status_code == 202
        jobs.append(mock_arq.enqueue_job.call_args.args[1:4])

    # The baseline is read before the graph (pipeline) and again inside it
    # (Critic), both as blocking calls. With them on the event loop: two
    # jobs x two reads, serialized, and the budget can't interrupt them.
    from app.services.llm_client import LLMClient
    llm_patch = patch.object(LLMClient, "complete", new=_slow_llm) if slow == "llm" else patch.object(
        LLMClient, "complete", new=LLMClient.complete)
    with patch.object(LedgerRepository, "get_baseline", new=_slow_baseline), llm_patch, \
         patch.object(pipeline.settings, "review_latency_budget_seconds", BUDGET_SECONDS):
        started = time.monotonic()
        await asyncio.gather(*(run_review_job({}, *job) for job in jobs))
        elapsed = time.monotonic() - started

    for _, review_id, _ in jobs:
        row = fake_review_repo.rows[review_id]
        assert row["status_reason"].startswith("timed out"), row.get("status_reason")
    # Off the loop: both jobs read the baseline in parallel (~0.6 s), then
    # each graph is cut off by its 0.3 s budget (while a slowed model is
    # still "thinking", or while the Critic's own baseline read is still
    # running in a thread). On the loop the two pre-graph reads alone run
    # one after the other (1.2 s), and the Critic's reads can't be cut off.
    assert elapsed < BLOCK_SECONDS + BUDGET_SECONDS + 0.4, f"took {elapsed:.2f}s"


@pytest.mark.parametrize("route", [
    "get_stats", "get_repos", "get_repo_settings", "update_repo_settings", "get_repo_reviews",
    "get_review_detail", "get_hitl_pending", "get_ledger_trend", "get_ledger_stats",
])
def test_supabase_only_routes_run_in_the_thread_pool(route):
    # FastAPI runs a plain `def` route in its thread pool; an `async def`
    # route that calls sync Supabase blocks the event loop.
    assert not inspect.iscoroutinefunction(getattr(main_module, route))
