"""
Single source of truth for Redis connections in this project.

Redis is used for three things here: (1) the Arq job queue/broker for
review execution, (2) SSE pub/sub in app/services/stream_manager.py so
events reach a client connected to a different backend instance than the
one that enqueued the job (both from the Phase 2 Arq migration), and (3)
caching GitHub App installation access tokens, keyed by installation_id
(app/services/github_client.py, Phase 3) — explicitly blessed as a use of
the Redis already stood up in Phase 2, not a new cache layer. Nothing
beyond these three should reach for Redis without deciding that
deliberately, the same way each of these three was.
"""
from functools import lru_cache

import redis as sync_redis
import redis.asyncio as redis
from arq import create_pool
from arq.connections import ArqRedis, RedisSettings

from app.config import get_settings


@lru_cache
def get_redis_settings() -> RedisSettings:
    """Arq's own connection settings, derived from the same REDIS_URL
    everything else in this module uses — one URL, one source of truth."""
    settings = get_settings()
    return RedisSettings.from_dsn(settings.redis_url)


@lru_cache
def get_pubsub_redis() -> "redis.Redis":
    """A plain async redis-py client for pub/sub and the SSE history list.
    Deliberately separate from the Arq pool below — Arq's pool is for job
    enqueue/status, this one is for stream_manager's pub/sub, and mixing
    them would couple two independent concerns for no benefit."""
    settings = get_settings()
    return redis.from_url(settings.redis_url, decode_responses=True)


@lru_cache
def get_sync_redis() -> "sync_redis.Redis":
    """A synchronous client, deliberately separate from get_pubsub_redis()
    above. GitHubClient.__init__ (app/services/github_client.py) is called
    synchronously from several call sites, some inside LangGraph nodes
    that are themselves sync functions (agent_1_gate, finalize_and_post)
    — making the token cache lookup async would force those to become
    async too, well beyond this task's scope. Same Redis instance either
    way; this is just a sync-compatible handle to it."""
    settings = get_settings()
    return sync_redis.from_url(settings.redis_url, decode_responses=True)


_arq_pool: ArqRedis | None = None


async def get_arq_pool() -> ArqRedis:
    """Lazily-created, process-wide Arq connection pool used by FastAPI to
    enqueue review jobs. Not cached via lru_cache since creating it is
    async; guarded manually instead."""
    global _arq_pool
    if _arq_pool is None:
        _arq_pool = await create_pool(get_redis_settings())
    return _arq_pool
