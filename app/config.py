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

    # GitHub OAuth (Sign in with GitHub) — separate credential pair from the
    # App's private key above. Used only for user login/session, never for
    # server-to-server installation calls.
    github_client_id: str = ""
    github_client_secret: str = ""

    # Session cookies issued after OAuth login
    session_cookie_name: str = "ignition_session"
    session_ttl_seconds: int = 60 * 60 * 24 * 7  # 7 days
    session_cookie_secure: bool = False  # set True behind HTTPS in prod

    # Used to build the OAuth redirect_uri and the post-login redirect target
    backend_base_url: str = "http://localhost:8000"
    frontend_base_url: str = "http://localhost:3000"

    # LLM
    llm_provider: str = ""
    llm_api_key: str = ""
    llm_model_name: str = ""

    # Supabase / pgvector
    supabase_url: str = ""
    supabase_key: str = ""

    # AST analyzer (persistent Bun service, not per-PR subprocess)
    ast_service_url: str = ""

    # Redis: backs both the Arq job queue (review execution) and the
    # cross-process SSE pub/sub (app/services/stream_manager.py). Nothing
    # else uses Redis — see the scope note in that module.
    redis_url: str = "redis://localhost:6379/0"

    # CORS: comma-separated list, e.g.
    # "http://localhost:3000,https://app.example.com". Defaults to the
    # local dev origin ONLY as a fallback when unset — there's no existing
    # "is this production" detection in this codebase (no APP_ENV/
    # ENVIRONMENT var, no other convention) to gate a hard requirement on,
    # so this stays a soft default rather than guessing at one.
    allowed_origins: str = "http://localhost:3000"

    @property
    def allowed_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()]

    # Graph behavior — deterministic bounds, not tuned at runtime
    hallucination_retry_cap: int = 3
    review_latency_budget_seconds: int = 60

    def __init__(self, **kwargs):
        super().__init__(
            github_app_id=kwargs.get("github_app_id", os.getenv("GITHUB_APP_ID", "")),
            github_private_key=kwargs.get("github_private_key", os.getenv("GITHUB_PRIVATE_KEY", "")),
            github_webhook_secret=kwargs.get("github_webhook_secret", os.getenv("GITHUB_WEBHOOK_SECRET", "")),
            github_client_id=kwargs.get("github_client_id", os.getenv("GITHUB_CLIENT_ID", "")),
            github_client_secret=kwargs.get("github_client_secret", os.getenv("GITHUB_CLIENT_SECRET", "")),
            session_cookie_name=kwargs.get("session_cookie_name", os.getenv("SESSION_COOKIE_NAME", "ignition_session")),
            session_ttl_seconds=int(kwargs.get("session_ttl_seconds", os.getenv("SESSION_TTL_SECONDS", str(60 * 60 * 24 * 7)))),
            session_cookie_secure=str(kwargs.get("session_cookie_secure", os.getenv("SESSION_COOKIE_SECURE", "false"))).lower() in ("1", "true", "yes"),
            backend_base_url=kwargs.get("backend_base_url", os.getenv("BACKEND_BASE_URL", "http://localhost:8000")),
            frontend_base_url=kwargs.get("frontend_base_url", os.getenv("FRONTEND_BASE_URL", "http://localhost:3000")),
            llm_provider=kwargs.get("llm_provider", os.getenv("LLM_PROVIDER", "qwen")),
            llm_api_key=kwargs.get("llm_api_key", os.getenv("LLM_API_KEY", "")),
            llm_model_name=kwargs.get("llm_model_name", os.getenv("LLM_MODEL_NAME", "qwen-3-480b")),
            supabase_url=kwargs.get("supabase_url", os.getenv("SUPABASE_URL", "")),
            supabase_key=kwargs.get("supabase_key", os.getenv("SUPABASE_SERVICE_KEY", "")),
            ast_service_url=kwargs.get("ast_service_url", os.getenv("AST_SERVICE_URL", "http://localhost:4000")),
            redis_url=kwargs.get("redis_url", os.getenv("REDIS_URL", "redis://localhost:6379/0")),
            allowed_origins=kwargs.get("allowed_origins", os.getenv("ALLOWED_ORIGINS", "http://localhost:3000")),
            hallucination_retry_cap=int(kwargs.get("hallucination_retry_cap", os.getenv("HALLUCINATION_RETRY_CAP", "3"))),
            review_latency_budget_seconds=int(kwargs.get("review_latency_budget_seconds", os.getenv("REVIEW_LATENCY_BUDGET_SECONDS", "60"))),
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()