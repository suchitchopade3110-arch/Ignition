"""
Persistence for authenticated users and their sessions.

Sessions are opaque server-side tokens (not JWTs) — the browser only ever
holds a random session id in an httpOnly cookie. The user's GitHub App
user token (and its refresh token) live only in the `sessions` row on the
server, encrypted at rest with MultiFernet (audit P1-1), so they never
round-trip through the client and a database read alone doesn't reveal
them. This is what get_current_user / check_repo_access in app/auth.py
read from.

Requires migrations_002_auth.sql (tables) and
migrations_017_session_refresh_tokens.sql (refresh columns).
"""
from datetime import datetime, timedelta, timezone
from functools import lru_cache

from cryptography.fernet import Fernet, InvalidToken, MultiFernet

from app.config import get_settings
from app.database import get_supabase


class UndecryptableSession(Exception):
    """A session whose token can't be decrypted with the configured keys —
    a legacy plaintext row from before P1-1, or a key that was rotated out.
    Callers treat it as logged out."""


@lru_cache
def _fernet() -> MultiFernet:
    keys = [k.strip() for k in get_settings().session_token_keys.split(",") if k.strip()]
    if not keys:
        raise RuntimeError("SESSION_TOKEN_KEYS is not configured; refusing to store GitHub tokens unencrypted")
    return MultiFernet([Fernet(k.encode()) for k in keys])


def encrypt_token(token: str) -> str:
    return _fernet().encrypt(token.encode()).decode()


def decrypt_token(ciphertext: str) -> str:
    try:
        return _fernet().decrypt(ciphertext.encode()).decode()
    except InvalidToken as exc:
        raise UndecryptableSession() from exc


def _parse_ts(raw: str | None) -> datetime | None:
    return datetime.fromisoformat(raw.replace("Z", "+00:00")) if raw else None


def _expiry(seconds: int | None) -> str | None:
    if not seconds:
        return None
    return (datetime.now(timezone.utc) + timedelta(seconds=int(seconds))).isoformat()


class AuthRepository:
    USERS_TABLE = "users"
    SESSIONS_TABLE = "sessions"

    def __init__(self):
        self._db = get_supabase()

    def get_or_create_user(self, github_id: int, login: str, name: str | None, avatar_url: str | None) -> dict:
        res = self._db.table(self.USERS_TABLE).select("*").eq("github_id", github_id).execute()
        if res.data:
            existing = res.data[0]
            updates = {"login": login, "name": name, "avatar_url": avatar_url}
            if updates != {"login": existing.get("login"), "name": existing.get("name"), "avatar_url": existing.get("avatar_url")}:
                updated = self._db.table(self.USERS_TABLE).update(updates).eq("id", existing["id"]).execute()
                return updated.data[0] if updated.data else {**existing, **updates}
            return existing

        row = {"github_id": github_id, "login": login, "name": name, "avatar_url": avatar_url}
        inserted = self._db.table(self.USERS_TABLE).insert(row).execute()
        return inserted.data[0] if inserted.data else row

    @staticmethod
    def _token_columns(access_token: str, expires_in: int | None, refresh_token: str | None,
                       refresh_token_expires_in: int | None) -> dict:
        return {
            "github_access_token": encrypt_token(access_token),
            "github_token_expires_at": _expiry(expires_in),
            "github_refresh_token": encrypt_token(refresh_token) if refresh_token else None,
            "github_refresh_token_expires_at": _expiry(refresh_token_expires_in),
        }

    def create_session(self, session_id: str, user_id: str, github_access_token: str, ttl_seconds: int,
                       expires_in: int | None = None, refresh_token: str | None = None,
                       refresh_token_expires_in: int | None = None) -> dict:
        now = datetime.now(timezone.utc)
        row = {
            "id": session_id,
            "user_id": user_id,
            **self._token_columns(github_access_token, expires_in, refresh_token, refresh_token_expires_in),
            "created_at": now.isoformat(),
            "expires_at": (now + timedelta(seconds=ttl_seconds)).isoformat(),
        }
        self._db.table(self.SESSIONS_TABLE).insert(row).execute()
        return row

    def update_session_tokens(self, session_id: str, access_token: str, expires_in: int | None,
                              refresh_token: str | None, refresh_token_expires_in: int | None) -> None:
        self._db.table(self.SESSIONS_TABLE).update(
            self._token_columns(access_token, expires_in, refresh_token, refresh_token_expires_in)
        ).eq("id", session_id).execute()

    def get_session_with_user(self, session_id: str) -> dict | None:
        """The live session with its tokens decrypted, or None if it doesn't
        exist or has expired. Raises UndecryptableSession for a row the
        configured keys can't read."""
        res = (
            self._db.table(self.SESSIONS_TABLE)
            .select("*, users(*)")
            .eq("id", session_id)
            .execute()
        )
        if not res.data:
            return None
        session = res.data[0]

        expires_at = _parse_ts(session.get("expires_at"))
        if not expires_at or expires_at <= datetime.now(timezone.utc):
            return None

        user = session.get("users")
        if not user:
            return None

        refresh = session.get("github_refresh_token")
        return {
            "session_id": session["id"],
            "github_access_token": decrypt_token(session["github_access_token"]),
            "github_token_expires_at": _parse_ts(session.get("github_token_expires_at")),
            "github_refresh_token": decrypt_token(refresh) if refresh else None,
            "github_refresh_token_expires_at": _parse_ts(session.get("github_refresh_token_expires_at")),
            "user": user,
        }

    def delete_session(self, session_id: str) -> None:
        self._db.table(self.SESSIONS_TABLE).delete().eq("id", session_id).execute()

    def purge_expired_sessions(self) -> int:
        """DELETE FROM sessions WHERE expires_at < now() (audit P1-1; run
        daily by the worker). Returns how many rows went."""
        res = (
            self._db.table(self.SESSIONS_TABLE)
            .delete()
            .lt("expires_at", datetime.now(timezone.utc).isoformat())
            .execute()
        )
        return len(res.data or [])
