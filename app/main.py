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

from fastapi import FastAPI, Request, Depends, HTTPException, APIRouter, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse

from app.config import get_settings
from app.security import verify_github_signature
from app.schemas.github import PullRequestWebhook
from app.services.ast_client import ASTClient
from app.graph.workflow import build_graph
from app.graph.state import ReviewState, Finding as GraphFinding

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
    User,
    Paginated,
)
from app.repositories.dashboard import ReviewRepository, RepoRepository
from app.services.stream_manager import stream_manager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Ignition")

# Enable CORS for the Next.js dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

settings = get_settings()
ast_client = ASTClient(base_url=settings.ast_service_url)
graph = build_graph()

review_repo = ReviewRepository()
repo_repo = RepoRepository()


def parse_diff(diff_text: str) -> tuple[int, int, int, list[dict]]:
    """
    Parses unified diff text to extract changed files count,
    additions, deletions, and structured file diffs.
    """
    if not diff_text:
        return 0, 0, 0, []

    files_changed = 0
    lines_added = 0
    lines_deleted = 0
    diffs = []

    current_file = None
    current_content = []
    file_additions = 0
    file_deletions = 0

    for line in diff_text.splitlines():
        if line.startswith("diff --git"):
            if current_file:
                diffs.append({
                    "file": current_file,
                    "additions": file_additions,
                    "deletions": file_deletions,
                    "content": "\n".join(current_content),
                })
            current_file = None
            current_content = []
            file_additions = 0
            file_deletions = 0
            files_changed += 1
        elif line.startswith("--- a/"):
            pass
        elif line.startswith("+++ b/"):
            current_file = line[6:]
            if current_file.startswith("b/"):
                current_file = current_file[2:]
        elif line.startswith("@@"):
            current_content.append(line)
        elif line.startswith("+") and not line.startswith("+++"):
            lines_added += 1
            file_additions += 1
            current_content.append(line)
        elif line.startswith("-") and not line.startswith("---"):
            lines_deleted += 1
            file_deletions += 1
            current_content.append(line)
        else:
            current_content.append(line)

    if current_file:
        diffs.append({
            "file": current_file,
            "additions": file_additions,
            "deletions": file_deletions,
            "content": "\n".join(current_content),
        })

    return files_changed, lines_added, lines_deleted, diffs


async def run_review_stream_task(event: PullRequestWebhook, review_id: str):
    """
    Asynchronous background task to fetch PR diff metadata, execute
    the LangGraph state machine, persist transitions to Supabase, and
    stream progress events to active subscribers.
    """
    logger.info("Starting background review for ID %s", review_id)

    # 1. Reconstruct pull request info from GitHub Integration
    title = f"PR #{event.pull_request.number}"
    author = "unknown"
    branch = "main"
    gh = None

    try:
        from app.services.github_client import GitHubClient
        gh = GitHubClient(installation_id=event.installation.id)
        pr = gh._client.get_repo(event.repository.full_name).get_pull(event.pull_request.number)
        title = pr.title
        author = pr.user.login
        branch = pr.head.ref
    except Exception as e:
        logger.exception("Failed to fetch PR info from GitHub API: %s", e)

    # Fetch Unified Diff
    diff_text = ""
    files_changed = 0
    lines_added = 0
    lines_deleted = 0
    parsed_diffs = []

    if gh:
        try:
            diff_text = gh.get_pr_diff(event.repository.full_name, event.pull_request.number)
            files_changed, lines_added, lines_deleted, parsed_diffs = parse_diff(diff_text)
        except Exception as e:
            logger.exception("Failed to fetch PR diff: %s", e)

    # Determine previous ACS score for regression tracking
    previous_acs_score = 100.0
    try:
        latest_completed_res = (
            review_repo._db.table("reviews")
            .select("acs_score")
            .eq("repo_full_name", event.repository.full_name)
            .eq("status", "completed")
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        if latest_completed_res.data and latest_completed_res.data[0].get("acs_score") is not None:
            previous_acs_score = float(latest_completed_res.data[0]["acs_score"])
    except Exception as e:
        logger.warning("Could not query baseline review: %s", e)

    # Save initial metadata
    review_repo.update_review(
        review_id,
        {
            "status": "running",
            "title": title,
            "author": author,
            "branch": branch,
            "diff_text": diff_text,
            "files_changed": files_changed,
            "lines_added": lines_added,
            "lines_deleted": lines_deleted,
            "previous_acs_score": previous_acs_score,
            "diffs": parsed_diffs,
        },
    )

    # Signal review start
    await stream_manager.publish(
        review_id,
        {
            "type": "review.started",
            "reviewId": review_id,
            "status": "running",
        },
    )

    # Setup progress trackers for parallel agents
    agents_progress = {
        "agent_1_gate": {
            "id": "agent_1_gate",
            "name": "Deterministic Rule Gate",
            "status": "running",
            "findingCount": 0,
        },
        "agent_2a_struct": {
            "id": "agent_2a_struct",
            "name": "Architecture Auditor",
            "status": "pending",
            "findingCount": 0,
        },
        "agent_2b_chaos": {
            "id": "agent_2b_chaos",
            "name": "Logic & Chaos Specialist",
            "status": "pending",
            "findingCount": 0,
        },
        "agent_2c_security": {
            "id": "agent_2c_security",
            "name": "Security Auditor",
            "status": "pending",
            "findingCount": 0,
        },
        "agent_3_critic": {
            "id": "agent_3_critic",
            "name": "Critic & Synthesizer",
            "status": "pending",
            "findingCount": 0,
        },
        "agent_4_autofix": {
            "id": "agent_4_autofix",
            "name": "Auto-Fix Generator",
            "status": "pending",
            "findingCount": 0,
        },
    }

    review_repo.update_review(review_id, {"agents": list(agents_progress.values())})
    await stream_manager.publish(
        review_id,
        {
            "type": "agent.started",
            "reviewId": review_id,
            "agentId": "agent_1_gate",
        },
    )

    try:
        # 2. Build Graph State
        ast_payload = await ast_client.analyze_git(
            repo_full_name=event.repository.full_name,
            pr_number=event.pull_request.number,
            clone_url=event.repository.clone_url,
            ref=event.pull_request.head_sha,
            base_ref=event.pull_request.base_sha,
        )

        initial_state = ReviewState.from_ast_payload(ast_payload, event)
        initial_state.diff_text = diff_text

        # 3. Stream graph steps
        async for state_update in graph.astream(initial_state):
            for node_name, node_output in state_update.items():
                if node_name == "agent_1_gate":
                    violation = node_output.get("hard_rule_violation", False)
                    agents_progress["agent_1_gate"]["status"] = "completed"
                    agents_progress["agent_1_gate"]["findingCount"] = 1 if violation else 0

                    review_repo.update_review(review_id, {"agents": list(agents_progress.values())})
                    await stream_manager.publish(
                        review_id,
                        {
                            "type": "agent.completed",
                            "reviewId": review_id,
                            "agentId": "agent_1_gate",
                            "findingCount": 1 if violation else 0,
                        },
                    )

                    if not violation:
                        # Fan out parallel specialists
                        for agent_id in ["agent_2a_struct", "agent_2b_chaos", "agent_2c_security"]:
                            agents_progress[agent_id]["status"] = "running"
                            await stream_manager.publish(
                                review_id,
                                {
                                    "type": "agent.started",
                                    "reviewId": review_id,
                                    "agentId": agent_id,
                                },
                            )
                        review_repo.update_review(
                            review_id, {"agents": list(agents_progress.values())}
                        )

                elif node_name in ("agent_2a_struct", "agent_2b_chaos", "agent_2c_security"):
                    findings = node_output.get("findings", [])
                    agents_progress[node_name]["status"] = "completed"
                    agents_progress[node_name]["findingCount"] = len(findings)

                    review_repo.update_review(review_id, {"agents": list(agents_progress.values())})
                    await stream_manager.publish(
                        review_id,
                        {
                            "type": "agent.completed",
                            "reviewId": review_id,
                            "agentId": node_name,
                            "findingCount": len(findings),
                        },
                    )

                    # Trigger Critic if specialists are done
                    if (
                        agents_progress["agent_2a_struct"]["status"] == "completed"
                        and agents_progress["agent_2b_chaos"]["status"] == "completed"
                        and agents_progress["agent_2c_security"]["status"] == "completed"
                        and agents_progress["agent_3_critic"]["status"] == "pending"
                    ):
                        agents_progress["agent_3_critic"]["status"] = "running"
                        review_repo.update_review(
                            review_id, {"agents": list(agents_progress.values())}
                        )
                        await stream_manager.publish(
                            review_id,
                            {
                                "type": "critic.started",
                                "reviewId": review_id,
                            },
                        )

                elif node_name == "agent_3_critic":
                    agents_progress["agent_3_critic"]["status"] = "completed"
                    verified = node_output.get("verified_findings", [])
                    findings_count = len(verified)
                    agents_progress["agent_3_critic"]["findingCount"] = findings_count

                    acs_score = node_output.get("acs_score")
                    hitl_severity = node_output.get("hitl_severity", "none")
                    is_regression = node_output.get("is_regression", False)
                    final_comment = node_output.get("final_comment_markdown")

                    # Map verified findings to schema format
                    mapped_findings = []
                    for idx, f in enumerate(verified):
                        mapped_findings.append({
                            "id": f"{review_id}-finding-{idx}",
                            "agentId": f.agent,
                            "severity": f.severity,
                            "file": f.file_path,
                            "line": f.line,
                            "description": f.description,
                            "rule": f.agent.replace("_", " ").title(),
                            "recommendation": f.description,
                            "suggestedFix": f.suggested_patch,
                        })

                    regression_alert = {
                        "isRegression": is_regression,
                        "ruleRegressed": "ACS Score Drop" if is_regression else None,
                        "previousScore": previous_acs_score,
                        "currentScore": acs_score,
                        "impact": "Code quality dropped below baseline" if is_regression else None,
                        "recommendation": "Review security or architecture findings"
                        if is_regression
                        else None,
                    }

                    review_repo.update_review(
                        review_id,
                        {
                            "agents": list(agents_progress.values()),
                            "acs_score": acs_score,
                            "hitl_severity": hitl_severity,
                            "findings": mapped_findings,
                            "findings_count": findings_count,
                            "final_comment_markdown": final_comment,
                            "regression": regression_alert,
                            "severity": hitl_severity,
                        },
                    )

                    await stream_manager.publish(
                        review_id,
                        {
                            "type": "critic.completed",
                            "reviewId": review_id,
                            "acsScore": acs_score,
                        },
                    )
                    await stream_manager.publish(
                        review_id,
                        {
                            "type": "acs.updated",
                            "reviewId": review_id,
                            "acsScore": acs_score,
                        },
                    )
                    if is_regression:
                        await stream_manager.publish(
                            review_id,
                            {
                                "type": "regression.detected",
                                "reviewId": review_id,
                            },
                        )

                elif node_name == "pause_for_human_approval":
                    review_repo.update_review(review_id, {"status": "waiting_hitl"})
                    await stream_manager.publish(
                        review_id,
                        {
                            "type": "waiting.hitl",
                            "reviewId": review_id,
                            "status": "waiting_hitl",
                        },
                    )

                elif node_name == "agent_4_autofix":
                    agents_progress["agent_4_autofix"]["status"] = "completed"
                    posted = node_output.get("autofix_posted", 0)
                    failed = node_output.get("autofix_failed", 0)
                    agents_progress["agent_4_autofix"]["findingCount"] = posted

                    review_repo.update_review(
                        review_id,
                        {
                            "agents": list(agents_progress.values()),
                            "autofix_posted": posted,
                            "autofix_failed": failed,
                        },
                    )
                    await stream_manager.publish(
                        review_id,
                        {
                            "type": "agent.completed",
                            "reviewId": review_id,
                            "agentId": "agent_4_autofix",
                            "findingCount": posted,
                        },
                    )

                elif node_name == "finalize_and_post":
                    review_repo.update_review(review_id, {"status": "completed"})

                    # Update Repository baseline stats
                    db_rev = review_repo.get_review(review_id)
                    final_acs = db_rev.get("acs_score") if db_rev else 100.0
                    repo_repo.update_repo_stats(
                        repo_full_name=event.repository.full_name,
                        acs_score=final_acs,
                        last_review_at=datetime.utcnow().isoformat() + "Z",
                    )

                    await stream_manager.publish(
                        review_id,
                        {
                            "type": "review.completed",
                            "reviewId": review_id,
                            "status": "completed",
                        },
                    )

                elif node_name == "direct_rejection":
                    review_repo.update_review(
                        review_id,
                        {
                            "status": "completed",  # or rejected
                            "final_comment_markdown": node_output.get("final_comment_markdown"),
                        },
                    )
                    await stream_manager.publish(
                        review_id,
                        {
                            "type": "review.completed",
                            "reviewId": review_id,
                            "status": "completed",
                        },
                    )

    except Exception as exc:
        logger.exception("LangGraph execution failed: %s", exc)
        review_repo.update_review(review_id, {"status": "failed"})
        await stream_manager.publish(
            review_id,
            {
                "type": "review.failed",
                "reviewId": review_id,
                "status": "failed",
            },
        )


@app.post("/webhooks/github", status_code=202)
async def github_webhook(request: Request, _: None = Depends(verify_github_signature)):
    payload = await request.json()

    try:
        event = PullRequestWebhook.model_validate(payload)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Malformed webhook payload: {exc}")

    if event.action not in {"opened", "synchronize", "reopened"}:
        return {"status": "ignored", "action": event.action}

    review_id = str(uuid.uuid4())

    # Ensure repository is registered
    repo_repo.get_or_create_repo(event.repository.full_name)

    # Insert baseline review row
    review_repo.create_review(
        review_id=review_id,
        repo_full_name=event.repository.full_name,
        pr_number=event.pull_request.number,
        title=f"PR #{event.pull_request.number}",
        author="unknown",
        branch="main",
        commit_sha=event.pull_request.head_sha,
    )

    # Dispatch graph in background
    asyncio.create_task(run_review_stream_task(event, review_id))

    return {"reviewId": review_id, "status": "queued"}


# --- REST API Router ---
api_router = APIRouter(prefix="/api")


@api_router.get("/stats", response_model=DashboardStats)
async def get_stats():
    return DashboardStats(**review_repo.get_stats())


@api_router.get("/repos", response_model=list[Repository])
async def get_repos():
    return [Repository(**r) for r in repo_repo.list_repos()]


@api_router.get("/repos/{repo_id}/settings", response_model=RepositorySettings)
async def get_repo_settings(repo_id: str):
    return RepositorySettings(**repo_repo.get_or_create_settings(repo_id))


@api_router.patch("/repos/{repo_id}/settings", response_model=RepositorySettings)
async def update_repo_settings(repo_id: str, settings_update: dict):
    return RepositorySettings(**repo_repo.update_settings(repo_id, settings_update))


@api_router.get("/reviews", response_model=list[Review])
async def get_reviews(
    repo: str | None = None,
    status: str | None = None,
    severity: str | None = None,
):
    items, _ = review_repo.list_reviews(
        repo_name=repo, status=status, severity=severity, page=1, page_size=1000
    )
    return [Review(**i) for i in items]


@api_router.get("/repos/{repo_full_name:path}/reviews", response_model=list[Review])
async def get_repo_reviews(repo_full_name: str):
    items, _ = review_repo.list_reviews(repo_name=repo_full_name, page=1, page_size=1000)
    return [Review(**i) for i in items]


@api_router.get("/reviews/{id}", response_model=ReviewDetail)
async def get_review_detail(id: str):
    review = review_repo.get_review(id)
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    return ReviewDetail(**review)


@api_router.get("/hitl/pending", response_model=list[HitlItem])
async def get_hitl_pending():
    pending = review_repo.list_hitl_pending()
    now_str = datetime.utcnow().isoformat() + "Z"
    return [HitlItem(**{**r, "waiting_since": r.get("created_at", now_str)}) for r in pending]


@api_router.post("/hitl/{review_id}/approve", response_model=dict)
async def approve_hitl(review_id: str):
    review = review_repo.get_review(review_id)
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")

    review_repo.update_review(review_id, {"status": "completed"})

    # Post final comment to GitHub
    try:
        from app.services.github_client import GitHubClient

        # Load installation_id from baseline or configuration
        installation_id = 4226262  # Fallback standard
        gh = GitHubClient(installation_id=installation_id)
        gh.post_review_comment(
            repo_full_name=review["repo_name"],  # wait, repo_full_name in review is reconstructed
            pr_number=review["pull_request_number"],
            markdown_body=review.get("final_comment_markdown") or "Approved by human.",
        )
    except Exception as e:
        logger.exception("Failed to post human approval comment to GitHub: %s", e)

    # Publish hitl.approved and completed events
    await stream_manager.publish(review_id, {"type": "hitl.approved", "reviewId": review_id})
    await stream_manager.publish(
        review_id, {"type": "review.completed", "reviewId": review_id, "status": "completed"}
    )
    return {"success": True}


@api_router.post("/hitl/{review_id}/reject", response_model=dict)
async def reject_hitl(review_id: str):
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
async def get_ledger_trend(repo_full_name: str):
    return [LedgerTrend(**t) for t in review_repo.get_ledger_trend(repo_full_name)]


@api_router.get("/ledger/{repo_full_name:path}", response_model=LedgerStats)
async def get_ledger_stats(repo_full_name: str):
    return LedgerStats(**review_repo.get_ledger_stats(repo_full_name))


@api_router.get("/reviews/{review_id}/stream")
async def stream_review_events(review_id: str):
    """
    Subscribes to the event queue for the given review_id and yields
    Server-Sent Events (SSE). Closes automatically once a terminal
    state transition is reached.
    """
    queue = stream_manager.register(review_id)

    async def event_generator():
        try:
            while True:
                event = await queue.get()
                payload = SseEventPayload(**event)
                yield f"data: {payload.model_dump_json(by_alias=True)}\n\n"

                # Terminal event checks
                event_type = event.get("type")
                if event_type in ("review.completed", "review.failed", "waiting.hitl"):
                    logger.info("Closing stream for review %s on event %s", review_id, event_type)
                    break
        except asyncio.CancelledError:
            pass
        finally:
            stream_manager.disconnect(review_id, queue)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
        },
    )


# --- Root level stub routes (for exact apiGet layout.tsx compat) ---
@app.get("/auth/me", response_model=User)
@api_router.get("/auth/me", response_model=User)
async def auth_me():
    return User(id="user-1", name="Demo User")


@app.post("/auth/logout")
@api_router.post("/auth/logout")
async def auth_logout():
    return {"status": "ok"}


@app.get("/healthz")
async def healthz():
    return {"status": "ok"}


# --- Mount API router ---
app.include_router(api_router)