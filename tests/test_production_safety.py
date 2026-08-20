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


def test_samesite_none_is_accepted_unchanged_for_cross_site_deploys(caplog):
    # e.g. frontend and backend on two separate *.onrender.com subdomains
    # with no shared registrable domain — a valid, deliberate choice.
    s = _prod_settings(session_cookie_samesite="none")
    with caplog.at_level(logging.WARNING):
        s.validate_production_safety(logging.getLogger("test"))
    assert s.session_cookie_samesite == "none"
    assert not any("SAMESITE" in rec.message.upper() for rec in caplog.records)


def test_invalid_samesite_value_falls_back_to_lax_with_a_warning(caplog):
    s = _prod_settings(session_cookie_samesite="banana")
    with caplog.at_level(logging.WARNING):
        s.validate_production_safety(logging.getLogger("test"))
    assert s.session_cookie_samesite == "lax"
    assert any("SESSION_COOKIE_SAMESITE" in rec.message for rec in caplog.records)
