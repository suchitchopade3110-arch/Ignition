"""
GitHub webhook signature verification.

This was absent from the original skeleton. Without it, /webhooks/github
accepts unsigned POST bodies from anyone who finds the URL.
"""
import hashlib
import hmac

from fastapi import Request, HTTPException

from app.config import get_settings


async def verify_github_signature(request: Request) -> None:
    settings = get_settings()
    signature_header = request.headers.get("X-Hub-Signature-256")

    if not signature_header:
        raise HTTPException(status_code=401, detail="Missing X-Hub-Signature-256 header")

    body = await request.body()
    expected = "sha256=" + hmac.new(
        key=settings.github_webhook_secret.encode(),
        msg=body,
        digestmod=hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(expected, signature_header):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")