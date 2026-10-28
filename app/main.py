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
import hmac
import json
import logging
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any

from fastapi import FastAPI, Request, Response, Depends, HTTPException, APIRouter, BackgroundTasks, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse, PlainTextResponse
from postgrest.exceptions import APIError
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.services.rate_limiter import limiter
from app.services import metrics

from app.config import get_settings
from app.security import verify_github_signature, verify_csrf_token
from app.schemas.github import PullRequestWebhook
from app.services.redis_client import get_arq_pool
from app.services.review_pipeline import review_repo, repo_repo
from app.repositories.ledger import LedgerRepository
from app.auth import (
    router as auth_router,
    get_current_user,
    require_repo_full_name_access,
    require_repo_id_access,
    require_review_repo_access,
    check_repo_access,
    get_accessible_repos,
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
from app.services.schema_check import require_tables_or_exit
from app.services import check_runs

configure_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # A deploy that skipped a migration fails here, at startup, instead of
    # failing reviews later (audit P0-9). The Supabase client is sync.
    await asyncio.to_thread(require_tables_or_exit)
    yield


app = FastAPI(title="Ignition", lifespan=lifespan)

settings = get_settings()
settings.validate_production_safety(logger)

# Rate limiting (previously absent entirely — /webhooks/github and
# /auth/github/login were both unauthenticated-reachable and completely
# unthrottled). The Limiter instance itself lives in
# app/services/rate_limiter.py (see that module's docstring for why, and
# for the storage_uri tradeoff) — this just wires it into the app.
app.state.limiter = limiter


def _rate_limit_exceeded_handler_with_metric(request: Request, exc: RateLimitExceeded):
    metrics.rate_limit_exceeded_total.labels(path=request.url.path).inc()
    return _rate_limit_exceeded_handler(request, exc)


app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler_with_metric)
app.add_middleware(SlowAPIMiddleware)
# Constructed once here, at module import (same lifecycle as ast_client/
# graph in app/services/review_pipeline.py) — /readyz's LLM reachability
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


@app.middleware("http")
async def _record_http_metrics(request: Request, call_next):
    """
    Records ignition_http_requests_total / ignition_http_request_duration_seconds
    for every request. Uses request.scope["route"].path (the route
    TEMPLATE, e.g. "/api/reviews/{review_id}") rather than
    request.url.path — the raw path would create a distinct label series
    per review_id/repo_id ever requested, which is exactly the
    high-cardinality-label mistake Prometheus's own docs warn against and
    would make this endpoint grow without bound over the app's lifetime.
    Falls back to the raw path only for genuinely unmatched routes (404s),
    where there's no template to use and the raw path is bounded by
    "whatever a client tried," not by real traffic volume.
    """
    start = time.monotonic()
    response = await call_next(request)
    duration = time.monotonic() - start

    route = request.scope.get("route")
    path_label = route.path if route is not None else request.url.path

    metrics.http_requests_total.labels(
        method=request.method, path=path_label, status=str(response.status_code)
    ).inc()
    metrics.http_request_duration_seconds.labels(method=request.method, path=path_label).observe(duration)
    return response


@app.get("/metrics")
async def metrics_endpoint():
    """
    Prometheus scrape target. Unauthenticated like /healthz — a scraper
    needs to reach it without a session (same reasoning as /healthz's own
    docstring). Gated on METRICS_ENABLED (app/config.py) rather than always
    mounted, so a deployment that doesn't want operational metrics exposed
    can omit the endpoint entirely instead of relying on network-level
    blocking alone.
    """
    if not settings.metrics_enabled:
        raise HTTPException(status_code=404, detail="Not Found")
    return PlainTextResponse(generate_latest(), media_type=CONTENT_TYPE_LATEST)


def _handle_installation_event(event_type: str, payload: dict) -> None:
    """
    Registers/deregisters repos in response to the GitHub App being
    installed, uninstalled, or having its repo access changed —
    previously these events were only acknowledged (202), never acted on,
    so the dashboard's repo list only ever grew via a real pull_request
    webhook and never reflected an uninstall at all.

    Deliberately does NOT delete rows or their review history on
    uninstall — set_repo_installed just flips a flag (migrations_011),
    which is far cheaper to get wrong than data loss. What "uninstalled"
    means for the dashboard (hide it? show it grayed out?) is a frontend
    decision, not something to bake into this handler by deleting data it
    can't get back.

    Synchronous, not async: repo_repo's Supabase client is sync (like
    every other repo_repo call site in this file), and these events are
    low-frequency/low-latency-sensitive enough not to need dispatching to
    a background job the way review execution does.
    """
    if event_type == "installation":
        action = payload.get("action")
        repos = payload.get("repositories") or []
        if action in ("created", "unsuspend"):
            for repo in repos:
                full_name = repo.get("full_name")
                if not full_name:
                    continue
                repo_repo.get_or_create_repo(full_name)
                repo_repo.set_repo_installed(full_name, True)
            logger.info("Installation event: registered repos", extra={"action": action, "count": len(repos)})
        elif action in ("deleted", "suspend"):
            for repo in repos:
                full_name = repo.get("full_name")
                if full_name:
                    repo_repo.set_repo_installed(full_name, False)
            logger.info("Installation event: deregistered repos", extra={"action": action, "count": len(repos)})
        else:
            logger.info("Installation event action not actionable", extra={"action": action})

    elif event_type == "installation_repositories":
        action = payload.get("action")
        for repo in payload.get("repositories_added") or []:
            full_name = repo.get("full_name")
            if not full_name:
                continue
            repo_repo.get_or_create_repo(full_name)
            repo_repo.set_repo_installed(full_name, True)
        for repo in payload.get("repositories_removed") or []:
            full_name = repo.get("full_name")
            if full_name:
                repo_repo.set_repo_installed(full_name, False)
        logger.info(
            "Installation_repositories event processed",
            extra={
                "action": action,
                "added": len(payload.get("repositories_added") or []),
                "removed": len(payload.get("repositories_removed") or []),
            },
        )


@app.post("/webhooks/github", status_code=202)
@limiter.limit(settings.webhook_rate_limit)
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

    # GitHub App webhooks aren't only ever "pull_request" — "ping" (sent
    # once when the webhook is first configured) and "installation"/
    # "installation_repositories" (app installed/uninstalled/repos added or
    # removed) all land on this same URL if the App is subscribed to them.
    # Previously any non-pull_request delivery fell straight into
    # PullRequestWebhook.model_validate below and was rejected as a 422
    # "malformed payload" — technically true but misleading, since nothing
    # was actually malformed, this endpoint just didn't know any other
    # event existed.
    event_type = request.headers.get("X-GitHub-Event", "pull_request")
    logger.info("Webhook received", extra={"delivery_id": delivery_id, "event_type": event_type})
    if event_type in ("installation", "installation_repositories"):
        await asyncio.to_thread(_handle_installation_event, event_type, payload)
        metrics.webhook_events_total.labels(event_type=event_type, outcome="processed").inc()
        return {"status": "processed", "event": event_type}
    if event_type not in ("pull_request", "ping"):
        logger.info("Webhook event type not actionable, acknowledging without processing",
                     extra={"delivery_id": delivery_id, "event_type": event_type})
        metrics.webhook_events_total.labels(event_type=event_type, outcome="ignored").inc()
        return {"status": "ignored", "event": event_type}
    if event_type == "ping":
        metrics.webhook_events_total.labels(event_type="ping", outcome="processed").inc()
        return {"status": "pong"}

    try:
        event = PullRequestWebhook.model_validate(payload)
    except Exception as exc:
        logger.warning("Malformed webhook payload rejected", extra={"error": str(exc)})
        metrics.webhook_events_total.labels(event_type=event_type, outcome="rejected").inc()
        raise HTTPException(status_code=422, detail=f"Malformed webhook payload: {exc}")

    # A merged PR becomes part of the repo's regression baseline (audit
    # P0-7). One job per PR: Arq refuses a second job with the same id, so a
    # redelivered "closed" event doesn't double-write.
    if event.action == "closed" and event.pull_request.merged:
        pool = await get_arq_pool()
        await pool.enqueue_job(
            "record_merge_baseline", event.repository.full_name, event.pull_request.number,
            event.pull_request.head_sha,
            _job_id=f"baseline:{event.repository.full_name}:{event.pull_request.number}",
        )
        logger.info("Merge baseline job enqueued", extra={"pr_number": event.pull_request.number})
        metrics.webhook_events_total.labels(event_type=event_type, outcome="queued").inc()
        return {"status": "baseline_queued"}

    if event.action not in {"opened", "synchronize", "reopened", "ready_for_review"}:
        logger.info("Webhook action ignored", extra={"action": event.action})
        metrics.webhook_events_total.labels(event_type=event_type, outcome="ignored").inc()
        return {"status": "ignored", "action": event.action}
    if event.pull_request.draft:
        # Reviewed once it's marked ready (the ready_for_review action above).
        logger.info("Draft PR ignored", extra={"pr_number": event.pull_request.number})
        metrics.webhook_events_total.labels(event_type=event_type, outcome="ignored").inc()
        return {"status": "ignored", "reason": "draft"}

    review_id = str(uuid.uuid4())

    # Ensure repository is registered
    await asyncio.to_thread(repo_repo.get_or_create_repo, event.repository.full_name)

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
        await asyncio.to_thread(review_repo.create_review,
            review_id=review_id,
            repo_full_name=event.repository.full_name,
            pr_number=event.pull_request.number,
            title=f"PR #{event.pull_request.number}",
            author=event.pull_request.author_login,
            branch=event.pull_request.head_branch,
            commit_sha=event.pull_request.head_sha,
            installation_id=event.installation.id,
            correlation_id=correlation_id,
        )
    except APIError as exc:
        if exc.code == "23505" or "duplicate key" in (exc.message or "").lower():
            existing = await asyncio.to_thread(review_repo.get_review_by_repo_pr_sha,
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
            metrics.webhook_events_total.labels(event_type=event_type, outcome="duplicate").inc()
            return {
                "status": "duplicate",
                "reviewId": existing["id"] if existing else None,
                "detail": "A review for this repo/PR/head_sha already exists; no new run was started.",
            }
        raise

    # The "Ignition" check run (audit P0-6), created now so the PR shows a
    # queued check straight away. A GitHub hiccup here must never drop the
    # webhook: the job creates the check run itself if this didn't.
    try:
        check_run_id = await asyncio.to_thread(
            check_runs.create_check_run_sync,
            event.installation.id, event.repository.full_name, event.pull_request.head_sha,
        )
        await asyncio.to_thread(review_repo.update_review, review_id, {"check_run_id": check_run_id})
    except Exception:
        logger.exception("Could not create the GitHub check run", extra={"review_id": review_id})

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
    event_payload = event.model_dump(mode="json")
    try:
        pool = await get_arq_pool()
        # One job per (repo, PR, head SHA) (audit P1-8): Arq refuses a second
        # job with the same id, so a redelivered event can't run the same SHA twice.
        job = await pool.enqueue_job(
            "run_review_job", event_payload, review_id, correlation_id,
            _job_id=f"review:{event.repository.full_name}:{event.pull_request.number}:{event.pull_request.head_sha}",
        )
    except Exception:
        # Never leave a row "queued" with no job behind it (I-4). The partial
        # dedupe index lets a redelivery of this event create a fresh review.
        logger.exception("Could not enqueue the review job", extra={"review_id": review_id})
        status_reason = "failed: could not enqueue the review job"
        await asyncio.to_thread(review_repo.update_review, review_id, {"status": "failed", "status_reason": status_reason})
        await check_runs.conclude_check_run(
            reviews=review_repo, review_id=review_id, installation_id=event.installation.id,
            repo=event.repository.full_name, head_sha=event.pull_request.head_sha, conclusion="neutral",
            title=check_runs.could_not_finish_title(status_reason), summary=status_reason,
        )
        metrics.webhook_events_total.labels(event_type=event_type, outcome="enqueue_failed").inc()
        raise HTTPException(status_code=503, detail="Could not queue the review; redeliver the webhook to retry")
    # The event is kept so reconciliation can re-enqueue a lost job (I-4).
    await asyncio.to_thread(
        review_repo.update_review, review_id, {"job_id": job.job_id if job else None, "event_payload": event_payload}
    )
    logger.info("Review job enqueued", extra={"review_id": review_id, "job_id": job.job_id if job else None})
    metrics.webhook_events_total.labels(event_type=event_type, outcome="queued").inc()

    return {"reviewId": review_id, "status": "queued"}


# --- REST API Router ---
# Every /api/* route requires a valid session (401 if missing/expired).
# Repo-scoped routes layer an additional per-route ownership dependency
# (require_repo_full_name_access / require_repo_id_access /
# require_review_repo_access) that raises 403 if the signed-in user's
# GitHub token can't see that specific repo. See app/auth.py.
api_router = APIRouter(prefix="/api", dependencies=[Depends(get_current_user)])


@api_router.get("/stats", response_model=DashboardStats)
def get_stats(repos: frozenset[str] = Depends(get_accessible_repos)):
    return DashboardStats(**review_repo.get_stats(repo_names=repos))


@api_router.get("/repos", response_model=list[Repository])
def get_repos(repos: frozenset[str] = Depends(get_accessible_repos)):
    return [Repository(**r) for r in repo_repo.list_repos(repo_names=repos)]


@api_router.get("/repos/{repo_id}/settings", response_model=RepositorySettings)
def get_repo_settings(repo_id: str, _: AuthUser = Depends(require_repo_id_access)):
    return RepositorySettings(**repo_repo.get_or_create_settings(repo_id))


@api_router.patch("/repos/{repo_id}/settings", response_model=RepositorySettings, dependencies=[Depends(verify_csrf_token)])
def update_repo_settings(
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
    repos: frozenset[str] = Depends(get_accessible_repos),
):
    # Scoped to the caller's own repos (audit P0-4): with ?repo=, that one
    # repo after an access check; without it, every repo the caller can push
    # to. Never every tenant's reviews.
    if repo:
        await check_repo_access(request, repo)
        repos = frozenset({repo})
    # list_reviews already implemented real offset pagination (page/
    # page_size -> Supabase .range()) — this route just never exposed it,
    # hardcoding page=1/page_size=1000 and discarding the real `total`
    # count it already returns.
    items, total = await asyncio.to_thread(review_repo.list_reviews,
        repo_name=repo, status=status, severity=severity, page=page, page_size=page_size, repo_names=repos
    )
    return Paginated(items=[Review(**i) for i in items], page=page, page_size=page_size, total=total)


@api_router.get("/repos/{repo_full_name:path}/reviews", response_model=Paginated[Review])
def get_repo_reviews(
    repo_full_name: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
    _: AuthUser = Depends(require_repo_full_name_access),
):
    items, total = review_repo.list_reviews(repo_name=repo_full_name, page=page, page_size=page_size)
    return Paginated(items=[Review(**i) for i in items], page=page, page_size=page_size, total=total)


@api_router.get("/reviews/{review_id}", response_model=ReviewDetail)
def get_review_detail(review_id: str, _: AuthUser = Depends(require_review_repo_access)):
    review = review_repo.get_review(review_id)
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    return ReviewDetail(**review)


@api_router.get("/hitl/pending", response_model=list[HitlItem])
def get_hitl_pending(repos: frozenset[str] = Depends(get_accessible_repos)):
    pending = review_repo.list_hitl_pending(repo_names=repos)
    # Set (not incremented) from this query's own result each time it's
    # polled — see the metric's own docstring (app/services/metrics.py) for
    # why that's deliberate: it tracks the dashboard's actual source of
    # truth instead of a separately-maintained running count that could
    # drift from it.
    metrics.hitl_pending_gauge.set(len(pending))
    now_str = datetime.utcnow().isoformat() + "Z"
    return [HitlItem(**{**r, "waiting_since": r.get("created_at", now_str)}) for r in pending]


def _record_hitl_outcomes(review: dict, repo_full_name: str, review_id: str, outcome: str) -> None:
    """
    Records the human's approve/reject decision against every distinct
    finding pattern in this review (see agent_3_critic._finding_pattern_key
    and LedgerRepository.record_hitl_outcome) — not just the review row's
    own status column, which only ever tells you the outcome of whichever
    review last happened to contain a given pattern. Best-effort: a
    Supabase failure here must never fail the human's approve/reject
    action itself, since this is a forward-looking learning signal, not
    part of resolving the review.
    """
    pattern_keys = {f["patternKey"] for f in review.get("findings", []) if f.get("patternKey")}
    if not pattern_keys:
        return
    ledger = LedgerRepository()
    for pattern_key in pattern_keys:
        try:
            ledger.record_hitl_outcome(
                repo_full_name=repo_full_name, review_id=review_id, pattern_key=pattern_key, outcome=outcome,
            )
        except Exception:
            logger.exception(
                "Failed to record HITL outcome for pattern %s on review %s", pattern_key, review_id,
            )


@api_router.post("/hitl/{review_id}/approve", response_model=dict, dependencies=[Depends(verify_csrf_token)])
async def approve_hitl(review_id: str, _: AuthUser = Depends(require_review_repo_access)):
    review = await asyncio.to_thread(review_repo.get_review, review_id)
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
    gh_context = await asyncio.to_thread(review_repo.get_review_github_context, review_id)
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

    # Compare-and-set claim (audit P1-6): PostgREST's update ... eq(status)
    # is one UPDATE ... WHERE status = 'waiting_hitl' RETURNING, so exactly
    # one concurrent approve wins; every other gets 409 and posts nothing.
    reviews = review_repo._db.table(review_repo.TABLE)
    # status_changed_at lets reconciliation release a claim whose request
    # died between claim and post (I-4: posting > 5 min -> waiting_hitl).
    claimed = await asyncio.to_thread(
        reviews.update({"status": "posting", "status_changed_at": datetime.now(timezone.utc).isoformat()})
        .eq("id", review_id).eq("status", "waiting_hitl").execute
    )
    if not claimed.data:
        raise HTTPException(status_code=409, detail="Review is not awaiting approval")

    def _release_claim() -> None:
        # Post didn't happen: hand the review back so a human can retry.
        review_repo._db.table(review_repo.TABLE).update({"status": "waiting_hitl"}) \
            .eq("id", review_id).eq("status", "posting").execute()

    from app.services.github_client import GitHubClient

    def _client_and_head():
        client = GitHubClient(installation_id=gh_context["installation_id"])
        return client, client.get_pr_head_sha(gh_context["repo_full_name"], gh_context["pr_number"])

    try:
        # PyGithub is synchronous: off the event loop (audit P1-7).
        gh, current_head = await asyncio.to_thread(_client_and_head)
    except Exception as e:
        logger.exception("Failed to read the PR's current head from GitHub: %s", e)
        await asyncio.to_thread(_release_claim)
        raise HTTPException(status_code=502, detail="Could not reach GitHub to post the approval")
    # Same rule as the pipeline's "check again before posting" (audit P1-8):
    # the comment is sticky, so approving a review of an older commit would
    # overwrite the newer review's comment.
    if gh_context.get("commit_sha") and current_head and current_head != gh_context["commit_sha"]:
        await asyncio.to_thread(review_repo.update_review, review_id, {"status": "cancelled", "status_reason": f"superseded by {current_head}"})
        await _reconclude_check_run(review_id, gh_context, "neutral",
                                    check_runs.could_not_finish_title(f"superseded by {current_head}"))
        raise HTTPException(status_code=409, detail=f"This review is superseded by {current_head}; nothing was posted")

    # Post through the sticky comment (audit P1-8), so even a retried post
    # after a timeout is an edit, never a duplicate. A failure is surfaced
    # (502) and the claim released — never a silent "approved".
    try:
        logger.info("Posting HITL-approved comment to GitHub", extra={
            "review_id": review_id, "repo_full_name": gh_context["repo_full_name"], "pr_number": gh_context["pr_number"],
        })
        github_response = await asyncio.to_thread(
            gh.upsert_sticky_comment,
            repo_full_name=gh_context["repo_full_name"],
            pr_number=gh_context["pr_number"],
            body=gh_context.get("final_comment_markdown") or "Approved by human.",
            bot_login=gh.bot_login,
        )
    except Exception as e:
        logger.exception("Failed to post human approval comment to GitHub: %s", e)
        await asyncio.to_thread(_release_claim)
        raise HTTPException(status_code=502, detail=f"Failed to post approval comment to GitHub: {e}")

    logger.info("GitHub comment posted", extra={
        "review_id": review_id, "github_comment_url": github_response.get("html_url"),
    })
    await asyncio.to_thread(review_repo.update_review,
        review_id, {"status": "completed", "github_comment_preview": github_response.get("html_url")}
    )
    # Only now, after the post succeeded, is this a real approval worth
    # learning from (audit P1-6).
    await asyncio.to_thread(_record_hitl_outcomes, review, gh_context["repo_full_name"], review_id, "approved")
    # The check was left at action_required; it now reflects what was posted.
    conclusion, title = check_runs.posted_outcome(
        review.get("findings") or [], bool((review.get("status_reason") or "").startswith("incomplete")),
    )
    await _reconclude_check_run(review_id, gh_context, conclusion, title, gh_context.get("final_comment_markdown"))

    # Publish hitl.approved and completed events
    await stream_manager.publish(review_id, {"type": "hitl.approved", "reviewId": review_id})
    await stream_manager.publish(
        review_id, {"type": "review.completed", "reviewId": review_id, "status": "completed"}
    )
    metrics.hitl_resolutions_total.labels(outcome="approved").inc()
    return {
        "success": True,
        "github_comment_url": github_response.get("html_url"),
        "github_comment_id": github_response.get("id"),
    }


async def _reconclude_check_run(review_id: str, gh_context: dict, conclusion: str, title: str,
                                summary: str | None = None) -> None:
    """Moves a paused review's check off action_required once a human has
    decided (audit P0-6). Best-effort: the decision already stands."""
    if not gh_context.get("installation_id") or not gh_context.get("commit_sha"):
        return
    await check_runs.conclude_check_run(
        reviews=review_repo, review_id=review_id, installation_id=gh_context["installation_id"],
        repo=gh_context["repo_full_name"], head_sha=gh_context["commit_sha"],
        conclusion=conclusion, title=title, summary=summary or title,
    )


@api_router.post("/hitl/{review_id}/reject", response_model=dict, dependencies=[Depends(verify_csrf_token)])
async def reject_hitl(review_id: str, _: AuthUser = Depends(require_review_repo_access)):
    review = await asyncio.to_thread(review_repo.get_review, review_id)
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")

    # Same compare-and-set as approve (audit P1-6): only a review still
    # awaiting a human can be rejected, and only once.
    claimed = await asyncio.to_thread(
        review_repo._db.table(review_repo.TABLE).update({"status": "rejected"})
        .eq("id", review_id).eq("status", "waiting_hitl").execute
    )
    if not claimed.data:
        raise HTTPException(status_code=409, detail="Review is not awaiting approval")
    await asyncio.to_thread(review_repo.update_review, review_id, {"status": "rejected"})  # stamps completed_at/duration

    gh_context = await asyncio.to_thread(review_repo.get_review_github_context, review_id)
    if gh_context and gh_context.get("repo_full_name"):
        await asyncio.to_thread(_record_hitl_outcomes, review, gh_context["repo_full_name"], review_id, "rejected")
        await _reconclude_check_run(review_id, gh_context, "neutral", "Review dismissed by a maintainer")

    await stream_manager.publish(review_id, {"type": "hitl.rejected", "reviewId": review_id})
    await stream_manager.publish(
        review_id, {"type": "review.completed", "reviewId": review_id, "status": "rejected"}
    )
    metrics.hitl_resolutions_total.labels(outcome="rejected").inc()
    return {"success": True}


@api_router.get("/ledger/{repo_full_name:path}/trend", response_model=list[LedgerTrend])
def get_ledger_trend(repo_full_name: str, _: AuthUser = Depends(require_repo_full_name_access)):
    return [LedgerTrend(**t) for t in review_repo.get_ledger_trend(repo_full_name)]


@api_router.get("/ledger/{repo_full_name:path}", response_model=LedgerStats)
def get_ledger_stats(repo_full_name: str, _: AuthUser = Depends(require_repo_full_name_access)):
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
    gh_context = await asyncio.to_thread(review_repo.get_review_github_context, review_id)
    if gh_context and gh_context.get("correlation_id"):
        set_correlation_id(gh_context["correlation_id"])

    async def event_generator():
        # An SSE comment straight away: the Next.js rewrite (audit P0-5)
        # forwards response headers only with the first body byte, so
        # without this the browser's EventSource wouldn't open until the
        # first real event. Comment lines are ignored by EventSource.
        yield ": connected\n\n"
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
            # The stream now reaches the browser through the frontend's
            # Next.js rewrite (audit P0-5); tell any proxy not to buffer it.
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/livez")
async def livez():
    """Render's health check (I-5): is this process serving requests. No
    dependency calls, so a slow Groq or Supabase never gets the web service
    restarted and a poll costs nothing."""
    return {"status": "ok"}


# The deep check's last result, reused for 15 s so a poller can't turn it
# into a stream of Groq/Supabase calls (I-5).
_READYZ_CACHE_SECONDS = 15.0
_readyz_cache: dict = {}


@app.get("/readyz")
async def readyz(request: Request, response: Response):
    """
    Real dependency reachability (Supabase, the analyzer, the LLM provider,
    Redis — app/services/health_checks.py), for operators and monitors, not
    the platform probe. Requires `Authorization: Bearer $READYZ_TOKEN`;
    without a configured token it is 404 in production and open locally.
    Errors name only the exception class.
    """
    expected = settings.readyz_token
    if not expected:
        if settings.app_env == "production":
            raise HTTPException(status_code=404, detail="Not Found")
    else:
        supplied = request.headers.get("authorization", "")
        if not hmac.compare_digest(supplied.encode(), f"Bearer {expected}".encode()):
            raise HTTPException(status_code=401, detail="Missing or invalid token")

    now = time.monotonic()
    cached = _readyz_cache.get("result")
    if cached and now - cached[0] < _READYZ_CACHE_SECONDS:
        body, all_healthy = cached[1], cached[2]
    else:
        body, all_healthy = await run_health_checks()
        _readyz_cache["result"] = (now, body, all_healthy)
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