"""
Thin wrapper around the Groq SDK (OpenAI-compatible chat completions).
Isolated here so agent nodes don't import a provider SDK directly —
swapping providers later means changing this file only.

Retries with backoff on rate-limit/transient errors: Sub-Graphs A, B, C
fire in parallel per the graph's fan-out, which means three concurrent
calls land at once against Groq's free-tier 30 req/min cap. Without
retry, that's a routine 429, not an edge case.
"""
from groq import AsyncGroq
from groq import RateLimitError, APIConnectionError, APIStatusError
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from app.config import get_settings


class LLMClient:
    def __init__(self):
        settings = get_settings()
        self._client = AsyncGroq(api_key=settings.llm_api_key)
        self._model = settings.llm_model_name

    @retry(
        stop=stop_after_attempt(4),
        wait=wait_exponential(multiplier=1, min=2, max=20),
        retry=retry_if_exception_type((RateLimitError, APIConnectionError, APIStatusError)),
        reraise=True,
    )
    async def complete(self, prompt: str, json_mode: bool = True) -> str:
        response = await self._client.chat.completions.create(
            model=self._model,
            messages=[{"role": "user", "content": prompt}],
            # qwen3 models on Groq support reasoning_effort; 'none' disables
            # thinking mode for latency-sensitive review passes. Switch to
            # 'default' if findings quality needs the reasoning boost.
            reasoning_effort="none",
            response_format={"type": "json_object"} if json_mode else None,
        )
        return response.choices[0].message.content
