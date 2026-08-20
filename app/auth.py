"""
GitHub OAuth login, sessions, and per-repo authorization.

Flow:
  GET  /auth/github/login     -> redirect to GitHub's OAuth consent screen
  GET  /auth/github/callback  -> exchange code, upsert user, issue session cookie
  GET  /auth/me               -> current user (401 if no/invalid session)
  POST /auth/logout           -> destroy session

This is a *separate* credential pair from the GitHub App's private key in
app/security.py / app/services/github_client.py — that one signs JWTs for
server-to-server installation tokens. This one is a normal OAuth app used
only to establish "who is the human sitting at the browser."

Authorization model: a request for a specific repo is only allowed if the
signed-in user's own GitHub OAuth token can see that repo (GitHub's API
enforces this for us — we don't try to duplicate GitHub's permission model
locally). That access token is stored server-side in the `sessions` table
and never touches the browser.
"""
import logging
import secrets
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response
from pydantic import BaseModel

from app.config import get_settings
from app.repositories.auth import AuthRepository
from app.repositories.dashboard import RepoRepository, ReviewRepository
from app.services.rate_limiter import limiter

logger = logging.getLogger(__name__)

router = APIRouter(tags=["auth"])

_auth_repo = AuthRepository()
_repo_repo = RepoRepository()
_review_repo = ReviewRepository()

GITHUB_AUTHORIZE_URL = "https://github.com/login/oauth/authorize"
GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"
GITHUB_USER_URL = "https://api.github.com/user"
GITHUB_API_BASE = "https://api.github.com"

_OAUTH_STATE_COOKIE = "ignition_oauth_state"


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

async def get_current_user(request: Request) -> AuthUser:
    settings = get_settings()
    session_id = request.cookies.get(settings.session_cookie_name)
    if not session_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    try:
        session = _auth_repo.get_session_with_user(session_id)
    except Exception:
        logger.exception("Session lookup failed (datastore unreachable?)")
        raise HTTPException(status_code=503, detail="Auth service temporarily unavailable")

    if not session:
        raise HTTPException(status_code=401, detail="Session invalid or expired")

    u = session["user"]
    # Stashed for the repo-access dependencies below, and never sent back
    # to the client — request.state lives only for the life of this request.
    request.state.github_access_token = session["github_access_token"]
    return AuthUser(
        id=u["id"],
        github_id=u["github_id"],
        login=u["login"],
        name=u.get("name"),
        avatar_url=u.get("avatar_url"),
    )


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

    async with httpx.AsyncClient(timeout=10.0) as client:
        res = await client.get(
            f"{GITHUB_API_BASE}/repos/{repo_full_name}",
            headers={"Authorization": f"Bearer {access_token}", "Accept": "application/vnd.github+json"},
        )

    if res.status_code == 200:
        permissions = res.json().get("permissions") or {}
        if permissions.get("push") or permissions.get("admin") or permissions.get("maintain"):
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
    request: Request, repo_id: str, user: AuthUser = Depends(get_current_user)
) -> AuthUser:
    """Dependency for routes shaped /api/repos/{repo_id}/... where repo_id
    is the short `owner_name` form, not owner/name."""
    try:
        res = _repo_repo._db.table(_repo_repo.TABLE).select("owner", "name").eq("id", repo_id).execute()
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
        res = _review_repo._db.table(_review_repo.TABLE).select("repo_full_name").eq("id", review_id).execute()
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
    params = {
        "client_id": settings.github_client_id,
        "redirect_uri": redirect_uri,
        "scope": "read:user repo",
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
            logger.error("GitHub OAuth token exchange failed: %s", token_data)
            raise HTTPException(status_code=401, detail="GitHub OAuth token exchange failed")

        user_res = await client.get(
            GITHUB_USER_URL,
            headers={"Authorization": f"Bearer {access_token}", "Accept": "application/vnd.github+json"},
        )
        if user_res.status_code != 200:
            raise HTTPException(status_code=401, detail="Failed to fetch GitHub user profile")
        gh_user = user_res.json()

    user_row = _auth_repo.get_or_create_user(
        github_id=gh_user["id"],
        login=gh_user["login"],
        name=gh_user.get("name"),
        avatar_url=gh_user.get("avatar_url"),
    )

    session_id = _new_session_id()
    _auth_repo.create_session(
        session_id=session_id,
        user_id=user_row["id"],
        github_access_token=access_token,
        ttl_seconds=settings.session_ttl_seconds,
    )

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


@router.post("/auth/logout")
async def logout(request: Request, response: Response):
    settings = get_settings()
    session_id = request.cookies.get(settings.session_cookie_name)
    if session_id:
        _auth_repo.delete_session(session_id)
    response.delete_cookie(settings.session_cookie_name)
    response.delete_cookie(settings.csrf_cookie_name)
    return {"status": "ok"}


@router.get("/auth/me")
async def auth_me(user: AuthUser = Depends(get_current_user)):
    return user
