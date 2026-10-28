"""
Thin wrapper around the Groq SDK (OpenAI-compatible chat completions).
Isolated here so agent nodes don't import a provider SDK directly —
swapping providers later means changing this file only.

Retries with backoff on rate-limit/transient errors: Sub-Graphs A, B, C
fire in parallel per the graph's fan-out, which means three concurrent
calls land at once against Groq's free-tier 30 req/min cap. Without
retry, that's a routine 429, not an edge case.
"""
import logging
import time
from functools import lru_cache

from groq import AsyncGroq
from groq import RateLimitError, APIConnectionError, APITimeoutError, InternalServerError
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from app.config import get_settings

logger = logging.getLogger(__name__)


class LLMClient:
    def __init__(self):
        settings = get_settings()
        self._client = AsyncGroq(api_key=settings.llm_api_key)
        self._model = settings.llm_model_name
        self._reasoning_effort = settings.llm_reasoning_effort or None

    @property
    def model(self) -> str:
        return self._model

    @property
    def raw_client(self) -> AsyncGroq:
        """Exposes the underlying AsyncGroq instance for call shapes
        LLMClient doesn't wrap (e.g. app/services/health_checks.py's
        models.list() reachability check) — still the one shared instance,
        not a reason to construct a second AsyncGroq."""
        return self._client

    # Retry ONLY what can succeed on a second try: 429, 5xx, timeouts and
    # connection errors. A 400/401/404 (bad model id, bad key, bad param)
    # fails the same way every time — retrying it just burned ~14s of the
    # 60s review budget per dead call (audit P0-1).
    @retry(
        stop=stop_after_attempt(4),
        wait=wait_exponential(multiplier=1, min=2, max=20),
        retry=retry_if_exception_type((RateLimitError, APIConnectionError, APITimeoutError, InternalServerError)),
        reraise=True,
    )
    async def complete(self, prompt: str, json_mode: bool = True, agent_name: str = "unknown") -> str:
        """
        Logs the call boundary only — agent, model, timing, token usage,
        success/failure. Deliberately never logs prompt or response bodies
        (cost and sensitivity implications that's a separate decision from
        this task, not something to default into).
        """
        start = time.monotonic()
        logger.info("LLM call started", extra={"agent": agent_name, "model": self._model})
        try:
            kwargs = {}
            if self._reasoning_effort:
                kwargs["reasoning_effort"] = self._reasoning_effort
            if json_mode:
                kwargs["response_format"] = {"type": "json_object"}
            response = await self._client.chat.completions.create(
                model=self._model,
                messages=[{"role": "user", "content": prompt}],
                **kwargs,
            )
        except Exception:
            logger.exception("LLM call failed", extra={
                "agent": agent_name, "model": self._model,
                "duration_ms": int((time.monotonic() - start) * 1000),
            })
            raise

        usage = getattr(response, "usage", None)
        logger.info("LLM call completed", extra={
            "agent": agent_name,
            "model": self._model,
            "duration_ms": int((time.monotonic() - start) * 1000),
            "prompt_tokens": getattr(usage, "prompt_tokens", None),
            "completion_tokens": getattr(usage, "completion_tokens", None),
            "total_tokens": getattr(usage, "total_tokens", None),
        })
        content = response.choices[0].message.content
        if not content:
            # An empty completion is a failure, not "no findings".
            raise LLMEmptyResponseError(f"{agent_name}: empty completion from {self._model}")
        return content


class LLMEmptyResponseError(RuntimeError):
    pass


@lru_cache
def get_llm_client() -> "LLMClient":
    """
    Process-wide singleton, same pattern as app/database.py::get_supabase()
    and app/services/redis_client.py's cached getters — this codebase's
    existing convention for "one shared instance per process" is a cached
    module-level getter, not FastAPI Depends() (there's no per-route
    handler that calls the LLM directly to inject into — only graph nodes,
    which take `state: ReviewState`, and the /healthz check).

    AsyncGroq wraps an httpx.AsyncClient internally, which httpx documents
    as safe for concurrent use across many in-flight coroutines — that's
    the whole design point of an async client with connection pooling, not
    an incidental property. Constructing a fresh one per call (the
    previous behavior) was the anti-pattern, not this.
    """
    logger.info("Constructing shared LLMClient instance")
    return LLMClient()
