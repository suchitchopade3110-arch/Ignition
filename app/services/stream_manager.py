"""
Redis-backed SSE fan-out.

Replaces the previous in-memory (Dict[str, Set[asyncio.Queue]]) version —
that only worked because a single process both ran the review pipeline and
served the SSE endpoint. Now that review execution happens in an Arq
worker process (app/worker.py), a different process than the FastAPI
instance a client's EventSource is connected to, events have to cross a
process boundary to reach the browser. Redis pub/sub is that boundary, and
it also means the FastAPI process itself can be horizontally scaled — a
review enqueued via instance A streams correctly to a client connected to
instance B, because both only ever talk to Redis, never to each other.

Public API is unchanged from the in-memory version (`publish(review_id,
event)`), so every existing call site (approve_hitl, reject_hitl, and now
the Arq job in app/services/review_pipeline.py) needed zero changes beyond
becoming reachable from a different process. `register`/`disconnect`
(queue-based) are replaced by `stream(review_id)`, an async generator used
directly by the SSE endpoint in app/main.py.
"""
import json
import logging

from app.services.redis_client import get_pubsub_redis

logger = logging.getLogger(__name__)

# Late subscribers (a client reconnecting, or connecting after the review
# already started) need to see events that already happened — the history
# list plays that role Redis-side that the in-memory version played with a
# plain Python list per review_id. TTL bounds it to a review's realistic
# lifetime so it doesn't accumulate forever.
_HISTORY_TTL_SECONDS = 60 * 60 * 6  # 6 hours


def _channel(review_id: str) -> str:
    return f"review:{review_id}:events"


def _history_key(review_id: str) -> str:
    return f"review:{review_id}:history"


class ReviewStreamManager:
    async def publish(self, review_id: str, event: dict) -> None:
        r = get_pubsub_redis()
        payload = json.dumps(event)
        logger.info("SSE event published", extra={"review_id": review_id, "event_type": event.get("type")})
        # Order matters for the same reason it did with the in-memory
        # history dict: append-to-history before publish so a subscriber
        # that starts reading history mid-publish still sees this event
        # either via history or via the live channel, not neither.
        await r.rpush(_history_key(review_id), payload)
        await r.expire(_history_key(review_id), _HISTORY_TTL_SECONDS)
        await r.publish(_channel(review_id), payload)

    async def stream(self, review_id: str):
        """
        Async generator yielding raw event dicts for a review: history
        first (for late/reconnecting subscribers), then live events as
        they're published. Note: as with the original in-memory
        implementation, an event published in the narrow window between
        subscribing and reading history back can appear twice (once via
        history, once via the live channel) — this was already true
        before this migration and isn't something this rewrite needed to
        fix; frontend event handlers are idempotent enough that a
        duplicate agent.completed/etc. is harmless.
        """
        r = get_pubsub_redis()
        pubsub = r.pubsub()
        await pubsub.subscribe(_channel(review_id))
        try:
            history = await r.lrange(_history_key(review_id), 0, -1)
            for raw in history:
                yield json.loads(raw)

            async for message in pubsub.listen():
                if message.get("type") != "message":
                    continue
                yield json.loads(message["data"])
        finally:
            try:
                await pubsub.unsubscribe(_channel(review_id))
                await pubsub.aclose()
            except Exception:
                logger.exception("Error cleaning up pubsub subscription for review %s", review_id)


# Global singleton instance — same usage pattern as before, just backed by
# Redis instead of process memory.
stream_manager = ReviewStreamManager()
