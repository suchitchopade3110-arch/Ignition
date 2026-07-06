"""
Environment variables & API keys, loaded once and cached.
Keep ALL external config here — no os.getenv() calls scattered through the codebase.
"""
from functools import lru_cache
from pathlib import Path
from pydantic import BaseModel
import os

from dotenv import load_dotenv

# Load .env BEFORE anything reads os.getenv().
# Explicit path so it works regardless of the cwd uvicorn is launched from.
_env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=_env_path, override=True)


class Settings(BaseModel):
    """
    Field defaults are evaluated at *class-definition* time, which is too
    early — `load_dotenv()` hasn't run yet at that point.  We use
    `model_validator` instead so every `os.getenv()` call happens inside
    `Settings()`, i.e. after `load_dotenv()` above has executed.
    """
    # GitHub
    github_app_id: str = ""
    github_private_key: str = ""
    github_webhook_secret: str = ""

    # LLM
    llm_provider: str = ""
    llm_api_key: str = ""
    llm_model_name: str = ""

    # Supabase / pgvector
    supabase_url: str = ""
    supabase_key: str = ""

    # AST analyzer (persistent Bun service, not per-PR subprocess)
    ast_service_url: str = ""

    # Graph behavior — deterministic bounds, not tuned at runtime
    hallucination_retry_cap: int = 3
    review_latency_budget_seconds: int = 60

    def __init__(self, **kwargs):
        super().__init__(
            github_app_id=kwargs.get("github_app_id", os.getenv("GITHUB_APP_ID", "")),
            github_private_key=kwargs.get("github_private_key", os.getenv("GITHUB_PRIVATE_KEY", "")),
            github_webhook_secret=kwargs.get("github_webhook_secret", os.getenv("GITHUB_WEBHOOK_SECRET", "")),
            llm_provider=kwargs.get("llm_provider", os.getenv("LLM_PROVIDER", "qwen")),
            llm_api_key=kwargs.get("llm_api_key", os.getenv("LLM_API_KEY", "")),
            llm_model_name=kwargs.get("llm_model_name", os.getenv("LLM_MODEL_NAME", "qwen-3-480b")),
            supabase_url=kwargs.get("supabase_url", os.getenv("SUPABASE_URL", "")),
            supabase_key=kwargs.get("supabase_key", os.getenv("SUPABASE_SERVICE_KEY", "")),
            ast_service_url=kwargs.get("ast_service_url", os.getenv("AST_SERVICE_URL", "http://localhost:4000")),
            hallucination_retry_cap=int(kwargs.get("hallucination_retry_cap", os.getenv("HALLUCINATION_RETRY_CAP", "3"))),
            review_latency_budget_seconds=int(kwargs.get("review_latency_budget_seconds", os.getenv("REVIEW_LATENCY_BUDGET_SECONDS", "60"))),
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()