"""
GitHub OAuth login, sessions, and per-repo authorization.

Flow:
  GET  /auth/github/login     -> redirect to GitHub's OAuth consent screen
  GET  /auth/github/callback  -> exchange code, upsert user, issue session cookie
  GET  /auth/me               -> current user (401 if no/invalid session)
  POST /auth/logout           -> destroy session

Login goes through the GitHub App's own OAuth flow (audit P1-1): the App's
client id/secret, no scope parameter. A GitHub App user token can only do
what the App's permissions allow, on repos where the App is installed and
the user has access — never the old OAuth App's repo-wide `repo` scope.
This is a *separate* credential pair from the App's private key in
app/services/github_client.py, which signs JWTs for server-to-server
installation tokens; this one only establishes "who is the human sitting
at the browser."

Authorization model: a request for a specific repo is only allowed if the
signed-in user's own GitHub token can see that repo with write access
(GitHub's API enforces this for us). The token is stored server-side,
encrypted, in the `sessions` table and never touches the browser. Expiring
user tokens are refreshed here when they run out; logout revokes them.
"""
import asyncio
import json
import logging
import secrets
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response
from pydantic import BaseModel

from app.config import get_settings
from app.repositories.auth import AuthRepository, UndecryptableSession
from app.repositories.dashboard import RepoRepository, ReviewRepository
from app.services.rate_limiter import limiter
from app.services.redis_client import get_pubsub_redis

logger = logging.getLogger(__name__)

router = APIRouter(tags=["auth"])

_auth_repo = AuthRepository()
_repo_repo = RepoRepository()
_review_repo = ReviewRepository()

GITHUB_AUTHORIZE_URL = "https://github.com/login/oauth/authorize"
GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"
GITHUB_USER_URL = "https://api.github.com/user"
GITHUB_API_BASE = "https://api.github.com"
# Refresh a user token this long before GitHub says it expires.
_TOKEN_REFRESH_SKEW_SECONDS = 60

_OAUTH_STATE_COOKIE = "ignition_oauth_state"
# How long a user's resolved repo set is reused before asking GitHub again
# (audit P0-4). Short enough that a revoked collaborator drops off quickly.
_REPO_CACHE_TTL_SECONDS = 300


class AuthUser(BaseModel):
    id: str
    github_id: int
    login: str
    name: str | None = None
    avatar_url: str | None = None


def _new_session_id() -> str:
    return secrets.token_urlsafe(32)


# --- Dependencies used to protect /api/* routes -------------------------
# Defined before the route handlers below since /auth/me depends on
# get_current_user via FastAPI's Depends().

async def _logged_out(session_id: str, reason: str) -> HTTPException:
    """Ends a session that can't be used any more and returns the 401 to
    raise. Never a 500: the user just signs in again."""
    logger.info("Ending session: %s", reason)
    try:
        await asyncio.to_thread(_auth_repo.delete_session, session_id)
    except Exception:
        logger.warning("Could not delete the unusable session", exc_info=True)
    return HTTPException(status_code=401, detail="Session invalid or expired")


async def _refresh_user_token(session_id: str, session: dict) -> dict:
    """Swaps an expired GitHub App user token for a new one (audit P1-1).
    Refresh tokens are single-use, so when two requests race, the loser's
    refresh fails; it then re-reads the session and uses the winner's."""
    settings = get_settings()
    refresh_expires = session.get("github_refresh_token_expires_at")
    if not session.get("github_refresh_token") or (
        refresh_expires and refresh_expires <= datetime.now(timezone.utc)
    ):
        raise await _logged_out(session_id, "GitHub token expired and cannot be refreshed")
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            res = await client.post(
                GITHUB_TOKEN_URL,
                headers={"Accept": "application/json"},
                data={
                    "client_id": settings.github_client_id,
                    "client_secret": settings.github_client_secret,
                    "grant_type": "refresh_token",
                    "refresh_token": session["github_refresh_token"],
                },
            )
        data = res.json()
    except Exception:
        logger.warning("GitHub token refresh failed (network)", exc_info=True)
        raise HTTPException(status_code=503, detail="Could not refresh your GitHub sign-in; try again")

    if not data.get("access_token"):
        latest = await asyncio.to_thread(_auth_repo.get_session_with_user, session_id)
        if latest and latest.get("github_token_expires_at") and _token_is_fresh(latest):
            return latest  # another request refreshed it first
        raise await _logged_out(session_id, f"GitHub refused the token refresh ({data.get('error', 'no token')})")

    await asyncio.to_thread(
        _auth_repo.update_session_tokens, session_id, data["access_token"], data.get("expires_in"),
        data.get("refresh_token"), data.get("refresh_token_expires_in"),
    )
    return {**session, "github_access_token": data["access_token"]}


def _token_is_fresh(session: dict) -> bool:
    expires = session.get("github_token_expires_at")
    if not expires:
        return True  # token expiry is off for this App: tokens don't expire
    return expires > datetime.now(timezone.utc) + timedelta(seconds=_TOKEN_REFRESH_SKEW_SECONDS)


async def get_current_user(request: Request) -> AuthUser:
    settings = get_settings()
    session_id = request.cookies.get(settings.session_cookie_name)
    if not session_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    try:
        # Supabase is synchronous: off the event loop (audit P1-7).
        session = await asyncio.to_thread(_auth_repo.get_session_with_user, session_id)
    except UndecryptableSession:
        # A plaintext row from before P1-1, or a rotated-out key.
        raise await _logged_out(session_id, "stored token cannot be decrypted")
    except Exception:
        logger.exception("Session lookup failed (datastore unreachable?)")
        raise HTTPException(status_code=503, detail="Auth service temporarily unavailable")

    if not session:
        raise HTTPException(status_code=401, detail="Session invalid or expired")
    if not _token_is_fresh(session):
        session = await _refresh_user_token(session_id, session)

    u = session["user"]
    # Stashed for the repo-access dependencies below, and never sent back
    # to the client — request.state lives only for the life of this request.
    request.state.github_access_token = session["github_access_token"]
    user = AuthUser(
        id=u["id"],
        github_id=u["github_id"],
        login=u["login"],
        name=u.get("name"),
        avatar_url=u.get("avatar_url"),
    )
    request.state.auth_user = user
    return user


def _can_write(permissions: dict | None) -> bool:
    """Owner, collaborator or org member with write+ — the same rule for the
    cached repo set and the per-repo check below. Read access to a public
    repo does not count."""
    p = permissions or {}
    return bool(p.get("push") or p.get("maintain") or p.get("admin"))


async def get_accessible_repos(request: Request, user: AuthUser = Depends(get_current_user)) -> frozenset[str]:
    """
    Every repo the signed-in user can push to, resolved from GitHub once and
    cached in Redis for 5 minutes (audit P0-4). Every list endpoint filters
    by this set, so no user sees another tenant's reviews, stats, repos or
    HITL queue. A Redis problem only skips the cache; a GitHub problem is a
    502, never an unscoped result.
    """
    key = f"user_repos:{user.id}"
    redis = None
    try:
        redis = get_pubsub_redis()
        cached = await redis.get(key)
        if cached is not None:
            return frozenset(json.loads(cached))
    except Exception:
        logger.warning("Repo-set cache unavailable; resolving from GitHub", exc_info=True)

    token = getattr(request.state, "github_access_token", None)
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    # With GitHub App user tokens (audit P1-1) the set comes from the App's
    # installations the user can see, so it only lists repos where Ignition
    # is installed.
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"}
    repos: set[str] = set()
    async with httpx.AsyncClient(timeout=10.0) as client:

        async def pages(url: str, key: str):
            while url:
                res = await client.get(url, headers=headers)
                if res.status_code != 200:
                    logger.error("GitHub %s returned %s", url.split("?")[0], res.status_code)
                    raise HTTPException(status_code=502, detail="Could not resolve your repositories from GitHub")
                for item in res.json().get(key, []):
                    yield item
                url = res.links.get("next", {}).get("url")

        installation_ids = [i["id"] async for i in pages(f"{GITHUB_API_BASE}/user/installations?per_page=100", "installations")]
        for installation_id in installation_ids:
            url = f"{GITHUB_API_BASE}/user/installations/{installation_id}/repositories?per_page=100"
            async for repo in pages(url, "repositories"):
                if _can_write(repo.get("permissions")):
                    repos.add(repo["full_name"])

    if redis is not None:
        try:
            await redis.setex(key, _REPO_CACHE_TTL_SECONDS, json.dumps(sorted(repos)))
        except Exception:
            logger.warning("Could not cache the repo set", exc_info=True)
    return frozenset(repos)


async def check_repo_access(request: Request, repo_full_name: str) -> None:
    """
    A 200 from GET /repos/{full_name} is NOT sufficient by itself: any
    authenticated token can read a *public* repo's metadata regardless of
    who owns it, so that alone would let any logged-in user "access" every
    public repo on GitHub. We additionally require the `permissions` block
    GitHub returns for the authenticated caller to show real write/admin
    access — i.e. the user is the owner, a collaborator, or an org member
    with write+, not just someone who can view a public repo.
    """
    access_token = getattr(request.state, "github_access_token", None)
    if not access_token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    # The cached repo set answers most checks without a GitHub call (audit
    # P0-4, and the P2 "access check on every request" item). A repo not in
    # it — e.g. access granted in the last 5 minutes — still gets the
    # per-repo check below rather than a flat denial.
    user = getattr(request.state, "auth_user", None)
    if isinstance(user, AuthUser):
        try:
            if repo_full_name in await get_accessible_repos(request, user):
                return
        except HTTPException:
            pass

    async with httpx.AsyncClient(timeout=10.0) as client:
        res = await client.get(
            f"{GITHUB_API_BASE}/repos/{repo_full_name}",
            headers={"Authorization": f"Bearer {access_token}", "Accept": "application/vnd.github+json"},
        )

    if res.status_code == 200:
        if _can_write(res.json().get("permissions")):
            return
        raise HTTPException(
            status_code=403,
            detail=f"You do not have access to repository '{repo_full_name}'",
        )
    if res.status_code in (404, 403):
        raise HTTPException(
            status_code=403,
            detail=f"You do not have access to repository '{repo_full_name}'",
        )
    logger.error("Unexpected GitHub API response checking repo access for %s: %s", repo_full_name, res.status_code)
    raise HTTPException(status_code=502, detail="Could not verify repository access with GitHub")


async def require_repo_full_name_access(
    request: Request, repo_full_name: str, user: AuthUser = Depends(get_current_user)
) -> AuthUser:
    """Dependency for routes shaped /api/repos/{repo_full_name:path}/..."""
    await check_repo_access(request, repo_full_name)
    return user


async def require_repo_id_access(
    request: Request, repo_id: int, user: AuthUser = Depends(get_current_user)
) -> AuthUser:
    """Dependency for routes shaped /api/repos/{repo_id}/... where repo_id
    is GitHub's numeric repository id (P2 repo IDs)."""
    try:
        res = await asyncio.to_thread(
            _repo_repo._db.table(_repo_repo.TABLE).select("owner", "name").eq("github_repo_id", repo_id).execute
        )
    except Exception:
        logger.exception("Repo lookup failed (datastore unreachable?)")
        raise HTTPException(status_code=503, detail="Datastore temporarily unavailable")
    if not res.data:
        raise HTTPException(status_code=404, detail="Repository not found")
    repo_full_name = f"{res.data[0]['owner']}/{res.data[0]['name']}"
    await check_repo_access(request, repo_full_name)
    return user


async def require_review_repo_access(
    request: Request, review_id: str, user: AuthUser = Depends(get_current_user)
) -> AuthUser:
    """Dependency for routes keyed by review_id — resolves the review's
    owning repo first, then applies the same ownership check."""
    try:
        res = await asyncio.to_thread(
            _review_repo._db.table(_review_repo.TABLE).select("repo_full_name").eq("id", review_id).execute
        )
    except Exception:
        logger.exception("Review lookup failed (datastore unreachable?)")
        raise HTTPException(status_code=503, detail="Datastore temporarily unavailable")
    if not res.data:
        raise HTTPException(status_code=404, detail="Review not found")
    repo_full_name = res.data[0]["repo_full_name"]
    await check_repo_access(request, repo_full_name)
    return user


# --- OAuth login flow --------------------------------------------------

@router.get("/auth/github/login")
@limiter.limit(get_settings().auth_rate_limit)
async def github_login(request: Request):
    settings = get_settings()
    if not settings.github_client_id:
        raise HTTPException(status_code=500, detail="GITHUB_CLIENT_ID is not configured")

    state = secrets.token_urlsafe(24)
    redirect_uri = f"{settings.backend_base_url}/auth/github/callback"
    # No scope parameter (audit P1-1): GitHub App user tokens get exactly
    # the App's permissions, on repos where it's installed.
    params = {
        "client_id": settings.github_client_id,
        "redirect_uri": redirect_uri,
        "state": state,
    }
    response = Response(status_code=302)
    response.headers["Location"] = f"{GITHUB_AUTHORIZE_URL}?{urlencode(params)}"
    response.set_cookie(
        _OAUTH_STATE_COOKIE,
        state,
        max_age=600,
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite=settings.session_cookie_samesite,
    )
    return response


@router.get("/auth/github/callback")
@limiter.limit(get_settings().auth_rate_limit)
async def github_callback(
    request: Request,
    code: str | None = None,
    state: str | None = None,
    ignition_oauth_state: str | None = Cookie(default=None),
):
    settings = get_settings()

    if not code or not state or not ignition_oauth_state or state != ignition_oauth_state:
        raise HTTPException(status_code=400, detail="Invalid or missing OAuth state")

    async with httpx.AsyncClient(timeout=15.0) as client:
        token_res = await client.post(
            GITHUB_TOKEN_URL,
            headers={"Accept": "application/json"},
            data={
                "client_id": settings.github_client_id,
                "client_secret": settings.github_client_secret,
                "code": code,
                "redirect_uri": f"{settings.backend_base_url}/auth/github/callback",
            },
        )
        token_data = token_res.json()
        access_token = token_data.get("access_token")
        if not access_token:
            # Error fields only: a failed exchange has no token to leak, but
            # don't log the raw response anyway.
            logger.error("GitHub OAuth token exchange failed: %s", token_data.get("error"))
            raise HTTPException(status_code=401, detail="GitHub OAuth token exchange failed")

        user_res = await client.get(
            GITHUB_USER_URL,
            headers={"Authorization": f"Bearer {access_token}", "Accept": "application/vnd.github+json"},
        )
        if user_res.status_code != 200:
            raise HTTPException(status_code=401, detail="Failed to fetch GitHub user profile")
        gh_user = user_res.json()

    user_row = await asyncio.to_thread(
        _auth_repo.get_or_create_user,
        github_id=gh_user["id"],
        login=gh_user["login"],
        name=gh_user.get("name"),
        avatar_url=gh_user.get("avatar_url"),
    )

    session_id = _new_session_id()
    try:
        await asyncio.to_thread(
            _auth_repo.create_session,
            session_id=session_id,
            user_id=user_row["id"],
            github_access_token=access_token,
            ttl_seconds=settings.session_ttl_seconds,
            expires_in=token_data.get("expires_in"),
            refresh_token=token_data.get("refresh_token"),
            refresh_token_expires_in=token_data.get("refresh_token_expires_in"),
        )
    except RuntimeError:
        # SESSION_TOKEN_KEYS unset: fail closed rather than store a token in plaintext.
        logger.exception("Cannot create a session")
        raise HTTPException(status_code=500, detail="Login is not configured on this server")

    response = Response(status_code=302)
    response.headers["Location"] = f"{settings.frontend_base_url}/dashboard"
    response.delete_cookie(_OAUTH_STATE_COOKIE)
    response.set_cookie(
        settings.session_cookie_name,
        session_id,
        max_age=settings.session_ttl_seconds,
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite=settings.session_cookie_samesite,
    )
    # CSRF double-submit token (see app/security.py::verify_csrf_token) —
    # issued alongside the session, same lifetime, but deliberately NOT
    # httponly: the frontend's own JS reads this one and echoes it back as
    # a header on mutating requests. Not a signed/derived value on purpose
    # — a plain random token is exactly what the double-submit pattern
    # needs, and deriving it from the session would just make it
    # predictable from other data without adding any real protection.
    response.set_cookie(
        settings.csrf_cookie_name,
        secrets.token_urlsafe(32),
        max_age=settings.session_ttl_seconds,
        httponly=False,
        secure=settings.session_cookie_secure,
        samesite=settings.session_cookie_samesite,
    )
    return response


async def _revoke_github_token(token: str) -> None:
    """DELETE /applications/{client_id}/token (audit P1-1). Best-effort:
    the session row is deleted whether or not GitHub answers."""
    settings = get_settings()
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            res = await client.request(
                "DELETE",
                f"{GITHUB_API_BASE}/applications/{settings.github_client_id}/token",
                auth=(settings.github_client_id, settings.github_client_secret),
                json={"access_token": token},
                headers={"Accept": "application/vnd.github+json"},
            )
        if res.status_code not in (204, 404):
            logger.warning("GitHub token revocation returned %s", res.status_code)
    except Exception:
        logger.warning("GitHub token revocation failed", exc_info=True)


@router.post("/auth/logout")
async def logout(request: Request, response: Response):
    settings = get_settings()
    session_id = request.cookies.get(settings.session_cookie_name)
    if session_id:
        try:
            session = await asyncio.to_thread(_auth_repo.get_session_with_user, session_id)
        except Exception:
            session = None  # undecryptable or unreachable: nothing to revoke
        if session:
            await _revoke_github_token(session["github_access_token"])
        await asyncio.to_thread(_auth_repo.delete_session, session_id)
    response.delete_cookie(settings.session_cookie_name)
    response.delete_cookie(settings.csrf_cookie_name)
    return {"status": "ok"}


@router.get("/auth/me")
async def auth_me(user: AuthUser = Depends(get_current_user)):
    return user
