"""
Settings.validate_production_safety (app/config.py) — the APP_ENV=production
auto-correct/warn checks added after the deployment-readiness review.
"""
import logging

from app.config import Settings


def _prod_settings(**overrides) -> Settings:
    base = dict(
        app_env="production",
        session_cookie_secure=False,
        allowed_origins="http://localhost:3000",
        github_webhook_secret="a-real-secret",
    )
    base.update(overrides)
    return Settings(**base)


def test_noop_outside_production():
    s = Settings(app_env="development", session_cookie_secure=False)
    s.validate_production_safety(logging.getLogger("test"))
    assert s.session_cookie_secure is False  # untouched


def test_forces_secure_cookie_in_production():
    s = _prod_settings(session_cookie_secure=False)
    s.validate_production_safety(logging.getLogger("test"))
    assert s.session_cookie_secure is True


def test_warns_on_localhost_only_cors_in_production(caplog):
    s = _prod_settings(allowed_origins="http://localhost:3000")
    with caplog.at_level(logging.WARNING):
        s.validate_production_safety(logging.getLogger("test"))
    assert any("ALLOWED_ORIGINS" in rec.message for rec in caplog.records)


def test_warns_on_missing_webhook_secret_in_production(caplog):
    s = _prod_settings(github_webhook_secret="")
    with caplog.at_level(logging.WARNING):
        s.validate_production_safety(logging.getLogger("test"))
    assert any("GITHUB_WEBHOOK_SECRET" in rec.message for rec in caplog.records)


def test_no_warnings_when_production_config_is_sane(caplog):
    s = _prod_settings(
        session_cookie_secure=True,
        allowed_origins="https://app.example.com",
        github_webhook_secret="a-real-secret",
    )
    with caplog.at_level(logging.WARNING):
        s.validate_production_safety(logging.getLogger("test"))
    assert caplog.records == []
