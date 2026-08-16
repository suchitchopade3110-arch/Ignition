"""
Shared test fixtures.

Env vars are set here, before any `app.*` module is imported anywhere in
the test session — app/config.py's Settings are @lru_cache'd and several
modules (app/services/review_pipeline.py, app/main.py) read them at
*module import* time, not per-call. pytest imports conftest.py before
collecting/importing test modules, so this is the one place early enough
to guarantee these are in place first. All values below are dummy/fake —
no real secret is ever required to run this suite (see the mocking
approach in tests/test_integration_webhook_review_comment.py's docstring).
"""
import os

os.environ.setdefault("GITHUB_APP_ID", "12345")
os.environ.setdefault("GITHUB_PRIVATE_KEY", "-----BEGIN RSA PRIVATE KEY-----\nDUMMY\n-----END RSA PRIVATE KEY-----")
os.environ.setdefault("GITHUB_WEBHOOK_SECRET", "test-webhook-secret")
os.environ.setdefault("GITHUB_CLIENT_ID", "dummy-client-id")
os.environ.setdefault("GITHUB_CLIENT_SECRET", "dummy-client-secret")
os.environ.setdefault("LLM_API_KEY", "dummy-llm-key")
os.environ.setdefault("LLM_PROVIDER", "groq")
os.environ.setdefault("LLM_MODEL_NAME", "dummy-model")
os.environ.setdefault("SUPABASE_URL", "https://dummy-project.supabase.co")
os.environ.setdefault("SUPABASE_SERVICE_KEY", "dummy-service-key")
os.environ.setdefault("AST_SERVICE_URL", "http://localhost:4000")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
