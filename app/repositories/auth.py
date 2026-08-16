"""
Persistence for authenticated users and their sessions.

Sessions are opaque server-side tokens (not JWTs) — the browser only ever
holds a random session id in an httpOnly cookie. The GitHub user-to-server
OAuth access token lives exclusively in the `sessions` row on the server,
so it never round-trips through the client. This is what
get_current_user / require_repo_access in app/auth.py read from.

Requires the migration in docs/migrations/002_auth_and_sessions.sql to have
been applied to Supabase before any of this is reachable.
"""
from datetime import datetime, timedelta, timezone

from app.database import get_supabase


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

    def create_session(self, session_id: str, user_id: str, github_access_token: str, ttl_seconds: int) -> dict:
        now = datetime.now(timezone.utc)
        row = {
            "id": session_id,
            "user_id": user_id,
            "github_access_token": github_access_token,
            "created_at": now.isoformat(),
            "expires_at": (now + timedelta(seconds=ttl_seconds)).isoformat(),
        }
        self._db.table(self.SESSIONS_TABLE).insert(row).execute()
        return row

    def get_session_with_user(self, session_id: str) -> dict | None:
        res = (
            self._db.table(self.SESSIONS_TABLE)
            .select("*, users(*)")
            .eq("id", session_id)
            .execute()
        )
        if not res.data:
            return None
        session = res.data[0]

        expires_at_raw = session.get("expires_at")
        if not expires_at_raw:
            return None
        expires_at = datetime.fromisoformat(expires_at_raw.replace("Z", "+00:00"))
        if expires_at <= datetime.now(timezone.utc):
            return None

        user = session.get("users")
        if not user:
            return None

        return {
            "session_id": session["id"],
            "github_access_token": session["github_access_token"],
            "user": user,
        }

    def delete_session(self, session_id: str) -> None:
        self._db.table(self.SESSIONS_TABLE).delete().eq("id", session_id).execute()
