"""
FastAPI entrypoint and REST/SSE API router.

Responsibilities:
  - Receive & verify GitHub webhooks
  - Run the LangGraph analysis in the background
  - Persist intermediate state changes to Supabase
  - Stream events to the dashboard via SSE (in-memory queues)
  - Serve all REST endpoints expected by the Next.js frontend
"""
import asyncio
import json
import logging
import uuid
from datetime import datetime
from typing import Any

from fastapi import FastAPI, Request, Response, Depends, HTTPException, APIRouter, BackgroundTasks, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from postgrest.exceptions import APIError

from app.config import get_settings
from app.security import verify_github_signature
from app.schemas.github import PullRequestWebhook
from app.services.redis_client import get_arq_pool
from app.services.review_pipeline import review_repo, repo_repo
from app.auth import (
    router as auth_router,
    get_current_user,
    require_repo_full_name_access,
    require_repo_id_access,
    require_review_repo_access,
    check_repo_access,
    AuthUser,
)

# Import dashboard schemas & repositories
from app.schemas.dashboard import (
    Repository,
    Review,
    ReviewDetail,
    HitlItem,
    RepositorySettings,
    DashboardStats,
    LedgerStats,
    LedgerTrend,
    SseEventPayload,
    Paginated,
)
from app.services.stream_manager import stream_manager
from app.services.logging_config import configure_logging, set_correlation_id
from app.services.health_checks import run_health_checks
from app.services.llm_client import get_llm_client

configure_logging()
logger = logging.getLogger(__name__)

app = FastAPI(title="Ignition")

settings = get_settings()
# Constructed once here, at module import (same lifecycle as ast_client/
# graph in app/services/review_pipeline.py) — /healthz's LLM reachability
# check (app/services/health_checks.py) is this process's only caller, but
# it should still be the one shared instance, not a fresh AsyncGroq per
# health-check poll.
get_llm_client()

# Pagination bounds for /api/reviews and /api/repos/{repo_full_name}/reviews
# — the only two endpoints that had a hardcoded page_size=1000 before this.
# FastAPI's Query(ge=..., le=...) rejects (422) anything outside these
# bounds outright, rather than silently clamping — consistent with this
# project's "fail loudly" pattern elsewhere (Phase 1 auth, Phase 2 webhook
# dedupe) rather than quietly under-serving what was actually asked for.
DEFAULT_PAGE_SIZE = 25
MAX_PAGE_SIZE = 100

# Origins driven by ALLOWED_ORIGINS (comma-separated; see app/config.py) —
# falls back to the local dev origin only when unset. Everything else
# about the policy (credentials/methods/headers) is untouched.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# review_repo / repo_repo are imported from app.services.review_pipeline
# above rather than constructed here — that module is the one source of
# truth now that review execution happens in the Arq worker process
# (app/worker.py), not inside this FastAPI process.


@app.post("/webhooks/github", status_code=202)
async def github_webhook(request: Request, _: None = Depends(verify_github_signature)):
    payload = await request.json()
    delivery_id = request.headers.get("X-GitHub-Delivery")

    # Correlation ID: X-GitHub-Delivery when present (ties the log trace
    # back to GitHub's own delivery record), a fresh UUID as a fallback for
    # requests that somehow lack it (a hand-crafted test payload, mainly —
    # every real GitHub webhook sends this header). Set as early as
    # possible so even the malformed-payload rejection below is traceable.
    correlation_id = delivery_id or str(uuid.uuid4())
    set_correlation_id(correlation_id)
    logger.info("Webhook received", extra={"delivery_id": delivery_id})

    try:
        event = PullRequestWebhook.model_validate(payload)
    except Exception as exc:
        logger.warning("Malformed webhook payload rejected", extra={"error": str(exc)})
        raise HTTPException(status_code=422, detail=f"Malformed webhook payload: {exc}")

    if event.action not in {"opened", "synchronize", "reopened"}:
        logger.info("Webhook action ignored", extra={"action": event.action})
        return {"status": "ignored", "action": event.action}

    review_id = str(uuid.uuid4())

    # Ensure repository is registered
    repo_repo.get_or_create_repo(event.repository.full_name)

    # Idempotency: a duplicate delivery for the same (repo, PR, head commit)
    # must not spawn a second LangGraph run. Enforced as a DB-level unique
    # constraint (migrations_004_webhook_dedupe.sql) on
    # (repo_full_name, pr_number, commit_sha) rather than an app-level
    # check-then-insert, so two deliveries racing each other are still
    # serialized correctly by Postgres instead of both slipping past an
    # app-side check. This runs BEFORE the Arq job enqueue below — the
    # whole point is to stop the second run from starting at all, not to
    # detect and clean up after two runs already kicked off.
    try:
        review_repo.create_review(
            review_id=review_id,
            repo_full_name=event.repository.full_name,
            pr_number=event.pull_request.number,
            title=f"PR #{event.pull_request.number}",
            author="unknown",
            branch="main",
            commit_sha=event.pull_request.head_sha,
            installation_id=event.installation.id,
            correlation_id=correlation_id,
        )
    except APIError as exc:
        if exc.code == "23505" or "duplicate key" in (exc.message or "").lower():
            existing = review_repo.get_review_by_repo_pr_sha(
                repo_full_name=event.repository.full_name,
                pr_number=event.pull_request.number,
                commit_sha=event.pull_request.head_sha,
            )
            # This delivery's own correlation_id already covers the log
            # lines up to this point; switch to the ORIGINAL review's
            # correlation_id for this line specifically so it's
            # discoverable from either delivery's trace.
            if existing and existing.get("correlation_id"):
                set_correlation_id(existing["correlation_id"])
            logger.info(
                "Duplicate webhook delivery ignored",
                extra={
                    "delivery_id": delivery_id,
                    "repo_full_name": event.repository.full_name,
                    "pr_number": event.pull_request.number,
                    "head_sha": event.pull_request.head_sha,
                    "existing_review_id": existing["id"] if existing else None,
                },
            )
            return {
                "status": "duplicate",
                "reviewId": existing["id"] if existing else None,
                "detail": "A review for this repo/PR/head_sha already exists; no new run was started.",
            }
        raise

    # Dispatch the review as an Arq job instead of an in-process
    # asyncio.create_task — this is what lets it survive this FastAPI
    # process restarting, and run on a worker process that isn't even this
    # one. job_id is persisted on the review row (not just kept in Arq's
    # own internal state) so a later restart-reconciliation pass can query
    # "is this job actually still running" independently of Arq.
    # correlation_id is passed as its own explicit job argument, not
    # folded into the webhook payload dict where it'd be one more
    # unlabeled key nobody reading run_review_job's signature would think
    # to look for.
    pool = await get_arq_pool()
    job = await pool.enqueue_job("run_review_job", event.model_dump(mode="json"), review_id, correlation_id)
    review_repo.update_review(review_id, {"job_id": job.job_id if job else None})
    logger.info("Review job enqueued", extra={"review_id": review_id, "job_id": job.job_id if job else None})

    return {"reviewId": review_id, "status": "queued"}


# --- REST API Router ---
# Every /api/* route requires a valid session (401 if missing/expired).
# Repo-scoped routes layer an additional per-route ownership dependency
# (require_repo_full_name_access / require_repo_id_access /
# require_review_repo_access) that raises 403 if the signed-in user's
# GitHub token can't see that specific repo. See app/auth.py.
api_router = APIRouter(prefix="/api", dependencies=[Depends(get_current_user)])


@api_router.get("/stats", response_model=DashboardStats)
async def get_stats():
    return DashboardStats(**review_repo.get_stats())


@api_router.get("/repos", response_model=list[Repository])
async def get_repos():
    return [Repository(**r) for r in repo_repo.list_repos()]


@api_router.get("/repos/{repo_id}/settings", response_model=RepositorySettings)
async def get_repo_settings(repo_id: str, _: AuthUser = Depends(require_repo_id_access)):
    return RepositorySettings(**repo_repo.get_or_create_settings(repo_id))


@api_router.patch("/repos/{repo_id}/settings", response_model=RepositorySettings)
async def update_repo_settings(
    repo_id: str, settings_update: RepositorySettings, _: AuthUser = Depends(require_repo_id_access)
):
    settings_dict = settings_update.model_dump()
    return RepositorySettings(**repo_repo.update_settings(repo_id, settings_dict))


@api_router.get("/reviews", response_model=Paginated[Review])
async def get_reviews(
    repo: str | None = None,
    status: str | None = None,
    severity: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
    user: AuthUser = Depends(get_current_user),
    request: Request = None,
):
    # `repo` is an optional query filter here (unlike the path-scoped routes
    # below), so ownership is only checked when a specific repo is asked for.
    # With no filter this returns the caller's own cross-repo review history
    # from `list_reviews` — login is required, but it is not further scoped
    # per-repo since there is no single repo to check against.
    if repo:
        await check_repo_access(request, repo)
    # list_reviews already implemented real offset pagination (page/
    # page_size -> Supabase .range()) — this route just never exposed it,
    # hardcoding page=1/page_size=1000 and discarding the real `total`
    # count it already returns.
    items, total = review_repo.list_reviews(
        repo_name=repo, status=status, severity=severity, page=page, page_size=page_size
    )
    return Paginated(items=[Review(**i) for i in items], page=page, page_size=page_size, total=total)


@api_router.get("/repos/{repo_full_name:path}/reviews", response_model=Paginated[Review])
async def get_repo_reviews(
    repo_full_name: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
    _: AuthUser = Depends(require_repo_full_name_access),
):
    items, total = review_repo.list_reviews(repo_name=repo_full_name, page=page, page_size=page_size)
    return Paginated(items=[Review(**i) for i in items], page=page, page_size=page_size, total=total)


@api_router.get("/reviews/{review_id}", response_model=ReviewDetail)
async def get_review_detail(review_id: str, _: AuthUser = Depends(require_review_repo_access)):
    review = review_repo.get_review(review_id)
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    return ReviewDetail(**review)


@api_router.get("/hitl/pending", response_model=list[HitlItem])
async def get_hitl_pending():
    pending = review_repo.list_hitl_pending()
    now_str = datetime.utcnow().isoformat() + "Z"
    return [HitlItem(**{**r, "waiting_since": r.get("created_at", now_str)}) for r in pending]


@api_router.post("/hitl/{review_id}/approve", response_model=dict)
async def approve_hitl(review_id: str, _: AuthUser = Depends(require_review_repo_access)):
    review = review_repo.get_review(review_id)
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")

    # Resolve where the comment actually needs to go BEFORE mutating any
    # state. repo_full_name must be the raw owner/name pair — the mapped
    # `review` dict's "repo_name" field is deliberately just the short
    # display name (see ReviewRepository._map_review_row), which is what
    # caused this to post to the wrong place before. installation_id must
    # be the one captured from the original webhook event at review-creation
    # time (see github_webhook below), not a hardcoded fallback — a
    # hardcoded id silently posts through whichever installation that id
    # happens to belong to, which may not even have this repo installed.
    gh_context = review_repo.get_review_github_context(review_id)
    if not gh_context or not gh_context.get("repo_full_name") or not gh_context.get("installation_id"):
        raise HTTPException(
            status_code=409,
            detail=(
                f"Cannot resolve installation_id/repo_full_name for review {review_id} — "
                "refusing to post an approval comment to an unverified destination."
            ),
        )

    # This request has no X-GitHub-Delivery header of its own (it's a
    # plain HTTP call from the dashboard, not a webhook) — resume logging
    # under the SAME correlation ID the original webhook started, so this
    # leg of the trace is discoverable from the same grep as the rest.
    if gh_context.get("correlation_id"):
        set_correlation_id(gh_context["correlation_id"])

    review_repo.update_review(review_id, {"status": "completed"})

    # Post final comment to GitHub. A failure here is surfaced to the
    # caller (502), not swallowed — silently returning success while the
    # comment never posted is exactly the failure mode this fix closes.
    from app.services.github_client import GitHubClient

    try:
        logger.info("Posting HITL-approved comment to GitHub", extra={
            "review_id": review_id, "repo_full_name": gh_context["repo_full_name"], "pr_number": gh_context["pr_number"],
        })
        gh = GitHubClient(installation_id=gh_context["installation_id"])
        github_response = gh.post_review_comment(
            repo_full_name=gh_context["repo_full_name"],
            pr_number=gh_context["pr_number"],
            markdown_body=gh_context.get("final_comment_markdown") or "Approved by human.",
        )
    except Exception as e:
        logger.exception("Failed to post human approval comment to GitHub: %s", e)
        raise HTTPException(status_code=502, detail=f"Failed to post approval comment to GitHub: {e}")

    logger.info("GitHub comment posted", extra={
        "review_id": review_id, "github_comment_url": github_response.get("html_url"),
    })
    review_repo.update_review(review_id, {"github_comment_preview": github_response.get("html_url")})

    # Publish hitl.approved and completed events
    await stream_manager.publish(review_id, {"type": "hitl.approved", "reviewId": review_id})
    await stream_manager.publish(
        review_id, {"type": "review.completed", "reviewId": review_id, "status": "completed"}
    )
    return {
        "success": True,
        "github_comment_url": github_response.get("html_url"),
        "github_comment_id": github_response.get("id"),
    }


@api_router.post("/hitl/{review_id}/reject", response_model=dict)
async def reject_hitl(review_id: str, _: AuthUser = Depends(require_review_repo_access)):
    review = review_repo.get_review(review_id)
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")

    review_repo.update_review(review_id, {"status": "completed"})  # or failed/rejected

    await stream_manager.publish(review_id, {"type": "hitl.rejected", "reviewId": review_id})
    await stream_manager.publish(
        review_id, {"type": "review.completed", "reviewId": review_id, "status": "rejected"}
    )
    return {"success": True}


@api_router.get("/ledger/{repo_full_name:path}/trend", response_model=list[LedgerTrend])
async def get_ledger_trend(repo_full_name: str, _: AuthUser = Depends(require_repo_full_name_access)):
    return [LedgerTrend(**t) for t in review_repo.get_ledger_trend(repo_full_name)]


@api_router.get("/ledger/{repo_full_name:path}", response_model=LedgerStats)
async def get_ledger_stats(repo_full_name: str, _: AuthUser = Depends(require_repo_full_name_access)):
    return LedgerStats(**review_repo.get_ledger_stats(repo_full_name))


@api_router.get("/reviews/{review_id}/stream")
async def stream_review_events(review_id: str, _: AuthUser = Depends(require_review_repo_access)):
    """
    Subscribes to this review's Redis pub/sub channel (app/services/
    stream_manager.py) and forwards events as Server-Sent Events. Backed by
    Redis rather than in-process memory, so this works correctly even when
    the job that produces these events is running in a different process
    (the Arq worker) or a client is connected to a different FastAPI
    instance than whichever one originally received the webhook.

    Emits a named `event: <type>` line, not just bare `data:` — the
    frontend's EventSource consumer (hooks/use-review-stream.ts) listens
    via addEventListener("review.started", ...) etc., which never fires on
    an unnamed/default "message" event. The previous implementation only
    ever sent bare `data:` frames, so none of those listeners were
    actually firing before this fix — found while rewriting this endpoint
    for Redis, not something this migration introduced.
    """
    gh_context = review_repo.get_review_github_context(review_id)
    if gh_context and gh_context.get("correlation_id"):
        set_correlation_id(gh_context["correlation_id"])

    async def event_generator():
        try:
            async for event in stream_manager.stream(review_id):
                payload = SseEventPayload(**event)
                event_type = event.get("type", "message")
                yield f"event: {event_type}\ndata: {payload.model_dump_json(by_alias=True)}\n\n"

                # Terminal event checks
                if event_type in ("review.completed", "review.failed", "waiting.hitl"):
                    logger.info("Closing stream for review %s on event %s", review_id, event_type)
                    break
        except asyncio.CancelledError:
            pass

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
        },
    )


@app.get("/healthz")
async def healthz(response: Response):
    """
    Real dependency reachability, not a static ping — see
    app/services/health_checks.py. Intentionally NOT behind the Phase 1
    auth dependency: infra tooling (load balancers, uptime monitors,
    container orchestrators) needs to reach this without a session, which
    is the standard shape for a health-check endpoint and matches this
    route's existing placement (outside api_router already).
    """
    body, all_healthy = await run_health_checks()
    if not all_healthy:
        response.status_code = 503
    return body


# --- Mount routers ---
# auth_router carries the real /auth/github/login, /auth/github/callback,
# /auth/me, /auth/logout — replacing the hardcoded "Demo User" stubs that
# used to live here. It is intentionally NOT behind api_router's
# get_current_user dependency: login/callback must be reachable while
# logged out, and /auth/me and /auth/logout enforce their own auth inline
# (see app/auth.py) since they aren't under the /api prefix.
app.include_router(auth_router)
app.include_router(api_router)