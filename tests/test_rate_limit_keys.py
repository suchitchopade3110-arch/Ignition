"""
I-6: every user shared one rate-limit bucket behind the proxy (after P0-5
every browser request reaches the backend from the Next.js server). Limits
are now keyed by a hash of the session cookie, falling back to the client
IP, and uvicorn trusts the platform's X-Forwarded-For so that IP is the
real one.
"""
import hashlib
import re
from pathlib import Path

import yaml
from starlette.requests import Request

from app.config import get_settings
from app.services import rate_limiter

REPO = Path(__file__).resolve().parents[1]


def _request(cookies: dict | None = None, client=("203.0.113.9", 1234)) -> Request:
    cookie = "; ".join(f"{k}={v}" for k, v in (cookies or {}).items())
    headers = [(b"cookie", cookie.encode())] if cookie else []
    return Request({"type": "http", "headers": headers, "client": client, "method": "GET", "path": "/api/x",
                    "query_string": b""})


def test_signed_in_users_get_their_own_bucket_even_from_one_ip():
    name = get_settings().session_cookie_name
    a = rate_limiter.rate_limit_key(_request({name: "session-a"}))
    b = rate_limiter.rate_limit_key(_request({name: "session-b"}))
    assert a != b
    assert a == "s:" + hashlib.sha256(b"session-a").hexdigest()[:16]
    assert "session-a" not in a  # the raw session id never becomes a storage key


def test_anonymous_requests_fall_back_to_the_client_ip():
    assert rate_limiter.rate_limit_key(_request()) == "203.0.113.9"


def test_the_shared_limiter_uses_the_session_key():
    assert rate_limiter.limiter._key_func is rate_limiter.rate_limit_key


def test_uvicorn_trusts_the_platform_proxy_headers_everywhere_it_runs():
    flags = ("--proxy-headers", "--forwarded-allow-ips=*")
    services = {s["name"]: s for s in yaml.safe_load((REPO / "render.yaml").read_text())["services"]}
    assert all(f in services["ignition-backend"]["dockerCommand"].split() for f in flags)
    cmd = re.search(r"^CMD (\[.*\])$", (REPO / "Dockerfile").read_text(), re.M).group(1)
    assert all(f'"{f}"' in cmd for f in flags)
    compose = yaml.safe_load((REPO / "docker-compose.yml").read_text())
    assert all(f in compose["services"]["backend"]["command"].split() for f in flags)
