"""
I-8: the SSE stream had no heartbeat, so a stream whose worker died just
hung (and idle proxies could cut it). stream_manager.stream now reads with
pubsub.get_message(ignore_subscribe_messages=True, timeout=15) and yields
None when nothing arrived; the endpoint turns that into an SSE comment
(": keepalive"). Streams stop after 10 minutes (EventSource reconnects and
replays history). No asyncio.wait_for around __anext__: a timeout there
would cancel the generator for good.
"""
import asyncio
import inspect
import json
import time
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

import app.main as main_module
import app.services.redis_client as redis_client
import app.services.stream_manager as stream_module
from app.auth import AuthUser, get_current_user, require_review_repo_access


class FakePubSub:
    """Delivers queued messages; otherwise waits `timeout` and returns None,
    like redis-py's get_message(timeout=...)."""

    def __init__(self, messages=()):
        self.messages = list(messages)
        self.calls = []
        self.closed = False

    async def subscribe(self, channel):
        self.channel = channel

    async def get_message(self, ignore_subscribe_messages=False, timeout=0.0):
        self.calls.append((ignore_subscribe_messages, timeout))
        if self.messages:
            return self.messages.pop(0)
        await asyncio.sleep(timeout)
        return None

    async def listen(self):  # the old blocking path; must not be used
        raise AssertionError("stream() must poll with get_message(timeout=...), not listen()")
        yield  # pragma: no cover

    async def unsubscribe(self, channel):
        pass

    async def aclose(self):
        self.closed = True


def _redis(pubsub, history=()):
    r = MagicMock()
    r.pubsub.return_value = pubsub
    r.lrange = AsyncMock(return_value=[json.dumps(h) for h in history])
    return r


@pytest.mark.asyncio
async def test_an_idle_stream_yields_a_keepalive_within_the_timeout():
    pubsub = FakePubSub()
    with patch.object(stream_module, "get_pubsub_redis", return_value=_redis(pubsub)):
        gen = stream_module.stream_manager.stream("r1", keepalive_seconds=0.05)
        started = time.monotonic()
        first = await asyncio.wait_for(gen.__anext__(), timeout=1)  # the test's own guard only
        await gen.aclose()
    assert first is None and time.monotonic() - started < 0.5
    assert pubsub.calls[0] == (True, 0.05)


@pytest.mark.asyncio
async def test_history_then_live_messages_are_yielded():
    pubsub = FakePubSub([{"type": "message", "data": json.dumps({"type": "agent.started"})}])
    with patch.object(stream_module, "get_pubsub_redis",
                      return_value=_redis(pubsub, history=[{"type": "review.started"}])):
        gen = stream_module.stream_manager.stream("r1", keepalive_seconds=0.05)
        assert (await gen.__anext__())["type"] == "review.started"
        assert (await gen.__anext__())["type"] == "agent.started"
        await gen.aclose()


@pytest.mark.asyncio
async def test_streams_stop_after_their_time_cap_and_clean_up():
    pubsub = FakePubSub()
    with patch.object(stream_module, "get_pubsub_redis", return_value=_redis(pubsub)):
        items = [item async for item in stream_module.stream_manager.stream("r1", keepalive_seconds=0.02,
                                                                             max_seconds=0.1)]
    assert items and all(item is None for item in items)
    assert pubsub.closed


def test_the_default_cap_is_ten_minutes_and_keepalives_every_15_seconds():
    sig = inspect.signature(stream_module.ReviewStreamManager.stream)
    assert sig.parameters["keepalive_seconds"].default == 15
    assert sig.parameters["max_seconds"].default == 600


@pytest.mark.asyncio
async def test_the_endpoint_turns_none_into_an_sse_keepalive_comment(monkeypatch):
    user = AuthUser(id="u", github_id=1, login="u")
    main_module.app.dependency_overrides[get_current_user] = lambda: user
    main_module.app.dependency_overrides[require_review_repo_access] = lambda: user
    monkeypatch.setattr(main_module.review_repo, "get_review_github_context", lambda review_id: None)

    async def idle_then_done(review_id):
        yield None
        yield {"type": "review.completed", "reviewId": review_id, "status": "completed"}

    monkeypatch.setattr(main_module.stream_manager, "stream", idle_then_done)
    try:
        transport = httpx.ASGITransport(app=main_module.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            res = await client.get("/api/reviews/r1/stream")
    finally:
        main_module.app.dependency_overrides.clear()
    assert ": keepalive\n\n" in res.text and "event: review.completed" in res.text


def test_no_wait_for_around_the_stream_generator():
    for source in (inspect.getsource(stream_module), inspect.getsource(main_module.stream_review_events)):
        assert "__anext__" not in source


def test_the_pubsub_client_is_capped_at_100_connections(monkeypatch):
    captured = {}
    monkeypatch.setattr(redis_client.redis, "from_url", lambda url, **kw: captured.update(kw) or MagicMock())
    redis_client.get_pubsub_redis.cache_clear()
    try:
        redis_client.get_pubsub_redis()
    finally:
        redis_client.get_pubsub_redis.cache_clear()
    assert captured["max_connections"] == 100 and captured["decode_responses"] is True
