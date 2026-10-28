"""
Single shared slowapi Limiter instance.

Split into its own module rather than constructed inline in app/main.py so
app/auth.py (whose router app/main.py itself mounts) can import and
decorate its own routes (@limiter.limit(...)) without an app.auth <->
app.main circular import — app/main.py imports `auth_router` from
app.auth, so app.auth importing the limiter back from app.main would be
circular; both import it from here instead.

storage_uri defaults to in-process memory:// rather than Redis — this
project's own deploy topology (docker-compose.yml) runs a single `backend`
replica by default, so per-instance limiting is equivalent to global
limiting today, and it avoids making rate limiting a hard dependency on
Redis being reachable for every single request (including in the test
suite, which points REDIS_URL at nothing real — see tests/conftest.py).
Set RATE_LIMIT_STORAGE_URI to a real redis:// URL once backend replicas
> 1 so limits are shared across instances instead of each instance
enforcing its own separate budget.
"""
import hashlib

from slowapi import Limiter
from slowapi.util import get_remote_address
from starlette.requests import Request

from app.config import get_settings

_settings = get_settings()


def rate_limit_key(request: Request) -> str:
    """Per-session bucket, client IP only as the fallback (I-6). After P0-5
    every browser request reaches this service from the Next.js server, so
    an IP key would put every user in one bucket. The session id is hashed
    so it never becomes a storage key. The IP is the real client's because
    uvicorn runs with --proxy-headers --forwarded-allow-ips=* (Render web
    services are only reachable through Render's proxy)."""
    session_id = request.cookies.get(get_settings().session_cookie_name)
    if session_id:
        return "s:" + hashlib.sha256(session_id.encode()).hexdigest()[:16]
    return get_remote_address(request)


limiter = Limiter(
    key_func=rate_limit_key,
    storage_uri=_settings.rate_limit_storage_uri,
    default_limits=[_settings.default_rate_limit],
)
