"""
GITHUB_WEBHOOK_SECRET_PREVIOUS grace-period support in
app.security.verify_github_signature — lets GITHUB_WEBHOOK_SECRET be
rotated without dropping in-flight deliveries signed with the outgoing
secret. See docs/SECRET_ROTATION.md.
"""
import hashlib
import hmac

import pytest
from fastapi import HTTPException, Request
from unittest.mock import MagicMock

from app.config import get_settings
from app.security import verify_github_signature


def _signed_request(body: bytes, secret: str) -> Request:
    signature = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    req = MagicMock(spec=Request)
    req.headers = {"X-Hub-Signature-256": signature}

    async def _body():
        return body

    req.body = _body
    return req


@pytest.mark.asyncio
async def test_current_secret_verifies():
    settings = get_settings()
    body = b'{"action": "opened"}'
    req = _signed_request(body, settings.github_webhook_secret)
    await verify_github_signature(req)  # does not raise


@pytest.mark.asyncio
async def test_previous_secret_verifies_during_rotation_window(monkeypatch):
    settings = get_settings()
    outgoing_secret = "outgoing-secret-value"
    monkeypatch.setattr(settings, "github_webhook_secret_previous", outgoing_secret)

    body = b'{"action": "opened"}'
    req = _signed_request(body, outgoing_secret)
    await verify_github_signature(req)  # does not raise — grace period active


@pytest.mark.asyncio
async def test_neither_secret_matches_is_rejected(monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "github_webhook_secret_previous", "some-old-secret")

    body = b'{"action": "opened"}'
    req = _signed_request(body, "completely-wrong-secret")
    with pytest.raises(HTTPException) as exc_info:
        await verify_github_signature(req)
    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_previous_secret_unset_does_not_verify_arbitrary_signatures():
    """Guards against a trivial bug: an empty github_webhook_secret_previous
    must never be treated as "any secret matches"."""
    settings = get_settings()
    assert settings.github_webhook_secret_previous == ""  # default/unset

    body = b'{"action": "opened"}'
    req = _signed_request(body, "some-secret-that-is-not-the-real-one")
    with pytest.raises(HTTPException) as exc_info:
        await verify_github_signature(req)
    assert exc_info.value.status_code == 401
