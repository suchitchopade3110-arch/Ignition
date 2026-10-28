"""
Audit P1-1: dashboard login used a separate OAuth App with the full `repo`
scope and stored the user's token in plaintext. Login now goes through the
GitHub App's own OAuth flow (no scope parameter), tokens are encrypted at
rest with MultiFernet keys from SESSION_TOKEN_KEYS, expiring user tokens
are refreshed in get_current_user, logout revokes the token, and a daily
worker cron purges expired sessions. A session that can't be decrypted
(a legacy plaintext row) is treated as logged out, never a 500.
"""
from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qs, urlparse

import httpx
import pytest
from cryptography.fernet import Fernet

import app.auth as auth_module
import app.main as main_module
import app.repositories.auth as auth_repo_module
from app.config import get_settings
from tests.fake_supabase import FakeSupabase

KEY_NEW = Fernet.generate_key().decode()
KEY_OLD = Fernet.generate_key().decode()
USER = {"id": "u-1", "github_id": 42, "login": "octocat", "name": "Octo", "avatar_url": None}


@pytest.fixture
def keys(monkeypatch):
    # Patches the shared Settings object rather than rebuilding it: modules
    # hold references to it from import time.
    def use(value):
        monkeypatch.setattr(get_settings(), "session_token_keys", value)
        auth_repo_module._fernet.cache_clear()
    use(KEY_NEW)
    yield use
    monkeypatch.undo()
    auth_repo_module._fernet.cache_clear()


def _iso(delta_seconds):
    return (datetime.now(timezone.utc) + timedelta(seconds=delta_seconds)).isoformat()


@pytest.fixture
def db(monkeypatch, keys):
    db = FakeSupabase({"users": [dict(USER)], "sessions": []})
    monkeypatch.setattr(auth_module._auth_repo, "_db", db)
    return db


def _session_row(db, sid="sess-1", token=None, refresh=None, token_expires=3600, raw_token=None):
    enc = auth_repo_module.encrypt_token
    row = {
        "id": sid, "user_id": USER["id"],
        "github_access_token": raw_token if raw_token is not None else enc(token or "tok-current"),
        "github_refresh_token": enc(refresh) if refresh else None,
        "github_token_expires_at": _iso(token_expires) if token_expires is not None else None,
        "created_at": _iso(-60), "expires_at": _iso(86400),
    }
    db.tables["sessions"].append(row)
    return row


class GitHubStub:
    """Answers the GitHub OAuth/API calls the auth code makes."""

    def __init__(self, monkeypatch, refresh_ok=True):
        self.calls: list[tuple[str, str, dict]] = []
        self.refresh_ok = refresh_ok
        real_request = httpx.AsyncClient.request

        async def request(client, method, url, **kwargs):
            url = str(url)
            if not url.startswith(("https://github.com", "https://api.github.com")):
                return await real_request(client, method, url, **kwargs)
            self.calls.append((method, url, kwargs))
            req = httpx.Request(method, url)
            if url == "https://github.com/login/oauth/access_token":
                data = kwargs.get("data") or {}
                if data.get("grant_type") == "refresh_token":
                    if not self.refresh_ok:
                        return httpx.Response(200, json={"error": "bad_refresh_token"}, request=req)
                    return httpx.Response(200, json={
                        "access_token": "tok-refreshed", "expires_in": 28800,
                        "refresh_token": "ref-refreshed", "refresh_token_expires_in": 15811200}, request=req)
                return httpx.Response(200, json={
                    "access_token": "tok-login", "expires_in": 28800,
                    "refresh_token": "ref-login", "refresh_token_expires_in": 15811200}, request=req)
            if url == "https://api.github.com/user":
                return httpx.Response(200, json={"id": 42, "login": "octocat", "name": "Octo"}, request=req)
            if url.startswith("https://api.github.com/applications/"):
                return httpx.Response(204, request=req)
            raise AssertionError(f"unexpected GitHub call {method} {url}")

        monkeypatch.setattr(httpx.AsyncClient, "request", request)


async def _client_call(method, path, cookies=None, **kwargs):
    transport = httpx.ASGITransport(app=main_module.app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test", cookies=cookies or {}) as client:
        return await client.request(method, path, **kwargs)


# --- encryption -----------------------------------------------------------

def test_tokens_round_trip_and_look_like_fernet(keys):
    ciphertext = auth_repo_module.encrypt_token("gho_secret")
    assert ciphertext.startswith("gAAAA") and "gho_secret" not in ciphertext
    assert auth_repo_module.decrypt_token(ciphertext) == "gho_secret"


def test_an_old_key_in_the_second_slot_still_decrypts(keys):
    keys(KEY_OLD)
    old_ciphertext = auth_repo_module.encrypt_token("gho_secret")
    keys(f"{KEY_NEW},{KEY_OLD}")
    assert auth_repo_module.decrypt_token(old_ciphertext) == "gho_secret"
    new_ciphertext = auth_repo_module.encrypt_token("gho_secret")
    assert Fernet(KEY_NEW.encode()).decrypt(new_ciphertext.encode()) == b"gho_secret"  # new writes use slot 1


def test_missing_keys_fail_closed(keys):
    keys("")
    with pytest.raises(RuntimeError, match="SESSION_TOKEN_KEYS"):
        auth_repo_module.encrypt_token("gho_secret")


# --- login ------------------------------------------------------------------

@pytest.mark.asyncio
async def test_login_asks_for_no_oauth_scope(db):
    res = await _client_call("GET", "/auth/github/login")
    assert res.status_code == 302
    query = parse_qs(urlparse(res.headers["location"]).query)
    assert "scope" not in query
    assert query["client_id"] == [get_settings().github_client_id]


@pytest.mark.asyncio
async def test_callback_stores_encrypted_tokens_and_their_expiry(db, monkeypatch):
    stub = GitHubStub(monkeypatch)
    res = await _client_call("GET", "/auth/github/callback?code=c&state=s", cookies={"ignition_oauth_state": "s"})
    assert res.status_code == 302
    row = db.tables["sessions"][0]
    assert row["github_access_token"].startswith("gAAAA")
    assert auth_repo_module.decrypt_token(row["github_access_token"]) == "tok-login"
    assert auth_repo_module.decrypt_token(row["github_refresh_token"]) == "ref-login"
    expires = datetime.fromisoformat(row["github_token_expires_at"])
    assert timedelta(hours=7) < expires - datetime.now(timezone.utc) <= timedelta(hours=8)
    token_call = next(c for c in stub.calls if c[1].endswith("/login/oauth/access_token"))
    assert token_call[2]["data"]["client_id"] == get_settings().github_client_id


# --- get_current_user -------------------------------------------------------

@pytest.mark.asyncio
async def test_an_expired_access_token_is_refreshed(db, monkeypatch):
    stub = GitHubStub(monkeypatch)
    _session_row(db, token="tok-old", refresh="ref-old", token_expires=-10)
    res = await _client_call("GET", "/auth/me", cookies={"ignition_session": "sess-1"})
    assert res.status_code == 200 and res.json()["login"] == "octocat"
    refresh_call = next(c for c in stub.calls if (c[2].get("data") or {}).get("grant_type") == "refresh_token")
    assert refresh_call[2]["data"]["refresh_token"] == "ref-old"
    row = db.tables["sessions"][0]
    assert auth_repo_module.decrypt_token(row["github_access_token"]) == "tok-refreshed"
    assert auth_repo_module.decrypt_token(row["github_refresh_token"]) == "ref-refreshed"
    assert datetime.fromisoformat(row["github_token_expires_at"]) > datetime.now(timezone.utc)


@pytest.mark.asyncio
async def test_a_valid_access_token_is_not_refreshed(db, monkeypatch):
    stub = GitHubStub(monkeypatch)
    _session_row(db, token="tok-current", refresh="ref-old", token_expires=3600)
    res = await _client_call("GET", "/auth/me", cookies={"ignition_session": "sess-1"})
    assert res.status_code == 200
    assert stub.calls == []


@pytest.mark.asyncio
async def test_a_failed_refresh_logs_the_user_out(db, monkeypatch):
    GitHubStub(monkeypatch, refresh_ok=False)
    _session_row(db, token="tok-old", refresh="ref-old", token_expires=-10)
    res = await _client_call("GET", "/auth/me", cookies={"ignition_session": "sess-1"})
    assert res.status_code == 401
    assert db.tables["sessions"] == []


@pytest.mark.asyncio
async def test_losing_a_refresh_race_uses_the_winners_token(db, monkeypatch):
    # Refresh tokens are single-use. When parallel dashboard requests all
    # see the expired token, one refresh wins; the others must not log the
    # user out.
    stub = GitHubStub(monkeypatch, refresh_ok=False)
    row = _session_row(db, token="tok-old", refresh="ref-old", token_expires=-10)
    real = auth_module._auth_repo.get_session_with_user
    reads = []

    def get_session(sid):
        reads.append(sid)
        if len(reads) == 2:  # the winner's write lands between our two reads
            row.update(github_access_token=auth_repo_module.encrypt_token("tok-winner"),
                       github_token_expires_at=_iso(28800))
        return real(sid)
    monkeypatch.setattr(auth_module._auth_repo, "get_session_with_user", get_session)
    res = await _client_call("GET", "/auth/me", cookies={"ignition_session": "sess-1"})
    assert res.status_code == 200
    assert len(db.tables["sessions"]) == 1
    assert any((c[2].get("data") or {}).get("grant_type") == "refresh_token" for c in stub.calls)


@pytest.mark.asyncio
async def test_a_legacy_plaintext_session_is_logged_out_not_a_500(db, monkeypatch):
    GitHubStub(monkeypatch)
    _session_row(db, raw_token="gho_plaintext_legacy", token_expires=None)
    res = await _client_call("GET", "/auth/me", cookies={"ignition_session": "sess-1"})
    assert res.status_code == 401
    assert db.tables["sessions"] == []


# --- logout -----------------------------------------------------------------

@pytest.mark.asyncio
async def test_logout_revokes_the_token_then_deletes_the_session(db, monkeypatch):
    stub = GitHubStub(monkeypatch)
    _session_row(db, token="tok-current")
    res = await _client_call("POST", "/auth/logout", cookies={"ignition_session": "sess-1"})
    assert res.status_code == 200
    method, url, kwargs = next(c for c in stub.calls if "/applications/" in c[1])
    settings = get_settings()
    assert (method, url) == ("DELETE", f"https://api.github.com/applications/{settings.github_client_id}/token")
    assert kwargs["json"] == {"access_token": "tok-current"}
    assert kwargs["auth"] == (settings.github_client_id, settings.github_client_secret)
    assert db.tables["sessions"] == []


@pytest.mark.asyncio
async def test_logout_still_deletes_the_session_when_github_is_down(db, monkeypatch):
    real_request = httpx.AsyncClient.request

    async def down(client, method, url, **kwargs):
        if str(url).startswith("https://api.github.com"):
            raise httpx.ConnectError("down")
        return await real_request(client, method, url, **kwargs)
    monkeypatch.setattr(httpx.AsyncClient, "request", down)
    _session_row(db, token="tok-current")
    res = await _client_call("POST", "/auth/logout", cookies={"ignition_session": "sess-1"})
    assert res.status_code == 200
    assert db.tables["sessions"] == []


# --- expired-session purge ----------------------------------------------------

@pytest.mark.asyncio
async def test_daily_cron_purges_only_expired_sessions(db, monkeypatch):
    import app.worker as worker_module
    from app.repositories.auth import AuthRepository

    db.tables["sessions"] = [
        {"id": "gone", "user_id": "u-1", "github_access_token": "x", "expires_at": _iso(-60)},
        {"id": "kept", "user_id": "u-1", "github_access_token": "x", "expires_at": _iso(3600)},
    ]
    monkeypatch.setattr(auth_repo_module, "get_supabase", lambda: db)
    assert AuthRepository().purge_expired_sessions() == 1
    assert [r["id"] for r in db.tables["sessions"]] == ["kept"]

    crons = {c.name: c for c in worker_module.WorkerSettings.cron_jobs}
    job = next(c for name, c in crons.items() if "purge_expired_sessions" in name)
    assert job.hour == {3} or job.hour == 3  # once a day
