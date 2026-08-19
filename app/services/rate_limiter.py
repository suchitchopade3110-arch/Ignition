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
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.config import get_settings

_settings = get_settings()

limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=_settings.rate_limit_storage_uri,
    default_limits=[_settings.default_rate_limit],
)
