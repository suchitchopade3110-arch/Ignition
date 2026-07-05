"""
Environment variables & API keys, loaded once and cached.
Keep ALL external config here — no os.getenv() calls scattered through the codebase.
"""
from functools import lru_cache
from pydantic import BaseModel
import os


class Settings(BaseModel):
    # GitHub
    github_app_id: str = os.getenv("GITHUB_APP_ID", "")
    github_private_key: str = os.getenv("GITHUB_PRIVATE_KEY", "")
    github_webhook_secret: str = os.getenv("GITHUB_WEBHOOK_SECRET", "")

    # LLM
    llm_provider: str = os.getenv("LLM_PROVIDER", "qwen")  # re-verify pricing before locking in
    llm_api_key: str = os.getenv("LLM_API_KEY", "")
    llm_model_name: str = os.getenv("LLM_MODEL_NAME", "qwen-3-480b")

    # Supabase / pgvector
    supabase_url: str = os.getenv("SUPABASE_URL", "")
    supabase_key: str = os.getenv("SUPABASE_SERVICE_KEY", "")

    # AST analyzer (persistent Bun service, not per-PR subprocess)
    ast_service_url: str = os.getenv("AST_SERVICE_URL", "http://localhost:4000")

    # Graph behavior — deterministic bounds, not tuned at runtime
    hallucination_retry_cap: int = int(os.getenv("HALLUCINATION_RETRY_CAP", "3"))
    review_latency_budget_seconds: int = int(os.getenv("REVIEW_LATENCY_BUDGET_SECONDS", "60"))


@lru_cache
def get_settings() -> Settings:
    return Settings()