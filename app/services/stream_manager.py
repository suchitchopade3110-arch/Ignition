import asyncio
import logging
from typing import Dict, Set

logger = logging.getLogger(__name__)

# NOTE: This is an in-memory queue manager. It is suitable for single-process/worker local testing.
# For multi-worker production deployments (e.g. using gunicorn/uvicorn with workers > 1),
# this must be replaced with a Redis Pub/Sub or similar distributed message broker, as separate
# OS processes do not share memory space and will fail to route events between requests.
class ReviewStreamManager:
    def __init__(self):
        self._queues: Dict[str, Set[asyncio.Queue]] = {}
        self._history: Dict[str, list[dict]] = {}

    def register(self, review_id: str) -> asyncio.Queue:
        queue = asyncio.Queue()
        if review_id not in self._queues:
            self._queues[review_id] = set()
        self._queues[review_id].add(queue)

        # Replay event history so clients connecting late do not miss updates
        if review_id in self._history:
            for event in self._history[review_id]:
                queue.put_nowait(event)
        
        return queue

    def disconnect(self, review_id: str, queue: asyncio.Queue):
        if review_id in self._queues:
            self._queues[review_id].discard(queue)
            if not self._queues[review_id]:
                del self._queues[review_id]

    async def publish(self, review_id: str, event: dict):
        if review_id not in self._history:
            self._history[review_id] = []
        self._history[review_id].append(event)

        if review_id in self._queues:
            for queue in self._queues[review_id]:
                await queue.put(event)


# Global singleton instance
stream_manager = ReviewStreamManager()
