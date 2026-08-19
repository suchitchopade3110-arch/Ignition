"""
GitHub webhook signature verification, and the CSRF double-submit check
for cookie-authenticated mutating API routes.

Webhook verification was absent from the original skeleton. Without it,
/webhooks/github accepts unsigned POST bodies from anyone who finds the URL.
"""
import hashlib
import hmac
import logging

from fastapi import Request, HTTPException

from app.config import get_settings

logger = logging.getLogger(__name__)


def _matches(body: bytes, secret: str, signature_header: str) -> bool:
    if not secret:
        return False
    expected = "sha256=" + hmac.new(
        key=secret.encode(), msg=body, digestmod=hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature_header)


async def verify_github_signature(request: Request) -> None:
    settings = get_settings()
    signature_header = request.headers.get("X-Hub-Signature-256")

    if not signature_header:
        raise HTTPException(status_code=401, detail="Missing X-Hub-Signature-256 header")

    body = await request.body()

    # Checks the current secret first, then (if set) the previous one — see
    # GITHUB_WEBHOOK_SECRET_PREVIOUS in app/config.py and
    # docs/SECRET_ROTATION.md. This is what makes rotating this secret a
    # zero-downtime operation: without a grace period, the instant GitHub's
    # side is switched to a new secret, every delivery signed with it 401s
    # here until this side is *also* updated and restarted — an unavoidable
    # window of dropped webhooks (mitigated only by GitHub's own retry
    # schedule) with no way to verify the switch landed cleanly. Setting
    # GITHUB_WEBHOOK_SECRET_PREVIOUS to the outgoing secret during rotation
    # means both old- and new-signed deliveries verify correctly for as
    # long as that variable stays set.
    if _matches(body, settings.github_webhook_secret, signature_header):
        return
    if settings.github_webhook_secret_previous and _matches(
        body, settings.github_webhook_secret_previous, signature_header
    ):
        logger.warning(
            "Webhook verified against GITHUB_WEBHOOK_SECRET_PREVIOUS, not the "
            "current secret — rotation is in progress or GITHUB_WEBHOOK_SECRET_PREVIOUS "
            "was left set after it finished. Safe to unset once no more deliveries "
            "log this warning."
        )
        return

    raise HTTPException(status_code=401, detail="Invalid webhook signature")


async def verify_csrf_token(request: Request) -> None:
    """
    Double-submit-cookie CSRF check for cookie-authenticated, state-changing
    /api/* routes (PATCH repo settings, HITL approve/reject). No server-side
    token storage needed: the cookie is set non-httponly at login
    (app/auth.py::github_callback) specifically so this page's own
    JavaScript can read it and echo it back as a header — same-origin JS is
    the only thing that can do both "read this cookie" and "set an
    arbitrary header on the request" at once, which is exactly what a
    cross-site attacker forging a request via a plain form POST or an
    <img>/fetch-without-credentials trick cannot do.

    This is defense in depth, not the only CSRF mitigation here: the
    session cookie itself is already SameSite=Lax (app/config.py), which on
    its own blocks the classic cross-site form-POST CSRF case in modern
    browsers. This catches the remaining cases SameSite doesn't (older
    browsers, same-site-but-cross-subdomain attacks, and any future
    SameSite=None exception) without requiring a second round-trip to fetch
    a token before every mutation.

    Deliberately NOT applied to /auth/logout: the worst a forged logout
    achieves is logging the victim out, which is not a security boundary
    worth the extra complexity here. NOT applied to /webhooks/github either
    — that route is authenticated by HMAC signature (verify_github_signature
    above), not cookies, so CSRF (which specifically exploits ambient
    cookie auth) doesn't apply to it at all.
    """
    settings = get_settings()
    cookie_token = request.cookies.get(settings.csrf_cookie_name)
    header_token = request.headers.get(settings.csrf_header_name)

    if not cookie_token or not header_token or not hmac.compare_digest(cookie_token, header_token):
        raise HTTPException(status_code=403, detail="Missing or invalid CSRF token")