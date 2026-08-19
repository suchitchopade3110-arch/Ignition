"""
The actual review pipeline: diff fetch, LangGraph execution, Supabase
writes, SSE publishing. Extracted out of app/main.py (where it used to run
as an asyncio.create_task fire-and-forget coroutine inside the FastAPI
process) so it can run instead as an Arq job inside a separate worker
process (app/worker.py) — the whole point of this migration.

`run_review_job` is the Arq job function. Everything above it (ast_client,
graph, review_repo, repo_repo, parse_diff) is shared setup that both this
worker-side module and app/main.py need — main.py imports review_repo/
repo_repo from here rather than constructing its own separate instances,
so there's one source of truth instead of two.
"""
import asyncio
import logging
import time
from datetime import datetime

from app.config import get_settings
from app.schemas.github import PullRequestWebhook
from app.services.ast_client import ASTClient
from app.services.stream_manager import stream_manager
from app.services import metrics
from app.graph.workflow import build_graph
from app.graph.state import ReviewState
from app.repositories.dashboard import ReviewRepository, RepoRepository
from app.services.logging_config import set_correlation_id

logger = logging.getLogger(__name__)

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


async def run_review_job(ctx: dict, event_payload: dict, review_id: str, correlation_id: str) -> None:
    """
    Arq job entrypoint. `ctx` is Arq's per-job context (unused here beyond
    what Arq requires of the signature); `event_payload` is the webhook
    event as a plain dict (Arq job args must be serializable, so
    app/main.py passes `event.model_dump(mode="json")` rather than the
    Pydantic model itself — reconstructed here). `correlation_id` is passed
    as its own explicit argument (not folded into event_payload) — set
    once here via set_correlation_id, it's then automatically attached to
    every log line for the rest of this job, including inside the
    parallel agent_2a/2b/2c fan-out, via the contextvar in
    app/services/logging_config.py.

    Body is otherwise unchanged from the pre-migration
    run_review_stream_task: same Supabase writes, same stream_manager.publish
    calls, same graph execution. Only the execution context moved (worker
    process instead of an asyncio task inside the FastAPI process) and
    stream_manager.publish now goes over Redis instead of an in-process
    queue — the call sites didn't need to change.
    """
    set_correlation_id(correlation_id)
    event = PullRequestWebhook.model_validate(event_payload)
    logger.info("Starting background review", extra={"review_id": review_id})
    _job_start_time = time.monotonic()

    def _record_terminal_metric(status: str) -> None:
        """Called from every terminal exit point below (completed, failed,
        cancelled, timed-out-to-HITL) — one place recording both the
        outcome counter and the wall-clock duration histogram, so no exit
        path can update review status without also being counted here."""
        metrics.reviews_completed_total.labels(status=status).inc()
        metrics.review_duration_seconds.observe(time.monotonic() - _job_start_time)

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
    parsed_diffs = []

    if gh:
        try:
            diff_text = gh.get_pr_diff(event.repository.full_name, event.pull_request.number)
            _, _, _, parsed_diffs = parse_diff(diff_text)
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

    # Tracks whether agent_1_gate's *next* appearance in the stream is a
    # hallucination-retry re-entry (workflow.py's only edge back into
    # agent_1_gate is agent_3_critic's "retry_context_fetch" branch) rather
    # than the first, normal pass. Detected locally via "have we already
    # seen the critic once" instead of reading graph/state internals —
    # simple, and correct because retry_context_fetch is the ONLY path
    # back to agent_1_gate (confirmed in workflow.py).
    critic_seen_once = False

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

        # 3. Stream graph steps, bounded by review_latency_budget_seconds —
        # wraps ONLY the graph execution (not the diff fetch above it), per
        # the PRD's bounded-self-correction philosophy: this is wall-clock's
        # counterpart to the hallucination-retry cap, not a whole-request timeout.
        async def _stream_graph():
            nonlocal critic_seen_once
            async for state_update in graph.astream(initial_state):
                for node_name, node_output in state_update.items():
                    if node_name == "agent_1_gate":
                        if critic_seen_once:
                            # Retry re-entry, not the first pass: reset
                            # progress for every agent about to re-run, so
                            # this pass's started/completed transitions and
                            # findingCounts start clean instead of carrying
                            # over "completed" from pass 1. Without this,
                            # the "specialists done -> trigger critic" check
                            # below silently never fires on a retry, since
                            # it's gated on agent_3_critic still reading
                            # "pending" — which it isn't, after pass 1.
                            # agent_4_autofix is deliberately excluded: it
                            # only ever runs after a pass that does NOT
                            # retry, so it can't have stale "completed"
                            # state to clean up here.
                            for agent_id in (
                                "agent_2a_struct", "agent_2b_chaos", "agent_2c_security", "agent_3_critic",
                            ):
                                agents_progress[agent_id]["status"] = "pending"
                                agents_progress[agent_id]["findingCount"] = 0
                            agents_progress["agent_1_gate"]["status"] = "running"
                            await stream_manager.publish(
                                review_id,
                                {
                                    "type": "agent.started",
                                    "reviewId": review_id,
                                    "agentId": "agent_1_gate",
                                },
                            )

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
                        critic_seen_once = True
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
                        # Records the end of the AUTOMATED portion, not the
                        # review's full lifetime — a human's later
                        # /api/hitl/{id}/approve or /reject call
                        # (app/main.py) is what actually resolves it, and is
                        # counted separately via hitl_resolutions_total.
                        # Re-recording this same job's duration there too
                        # would double count review_duration_seconds against
                        # however long the review sat waiting on a human,
                        # which isn't graph execution time.
                        _record_terminal_metric("waiting_hitl")

                    elif node_name == "agent_4_autofix":
                        agents_progress["agent_4_autofix"]["status"] = "completed"
                        # Defense in depth: node_output should always be a dict
                        # (see agent_4_autofix.py), but guard against None here too.
                        node_output = node_output or {}
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
                        _record_terminal_metric("completed")

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
                        _record_terminal_metric("completed")

        try:
            await asyncio.wait_for(_stream_graph(), timeout=settings.review_latency_budget_seconds)
        except asyncio.TimeoutError:
            # The PRD's bounded self-correction principle (hallucination retries'
            # give up after a cap and flag for human) applied to wall-clock time
            # instead of retry count: don't leave the review hanging, don't just
            # silently drop it — force it into the same human-escalation terminal
            # state the graph already uses for a critical HITL gate
            # (route_hitl -> pause_for_human_approval in app/graph/routing.py),
            # since a timed-out review inherently has unverified/incomplete state
            # that a human should look at, not an automated pass/fail verdict.
            logger.warning(
                "Review %s exceeded latency budget (%ds) — flagging for human review",
                review_id, settings.review_latency_budget_seconds,
            )
            review_repo.update_review(
                review_id,
                {
                    "status": "waiting_hitl",
                    "hitl_severity": "critical",
                    "severity": "critical",
                    "status_reason": f"timed out — exceeded review_latency_budget_seconds ({settings.review_latency_budget_seconds}s)",
                },
            )
            await stream_manager.publish(
                review_id,
                {
                    "type": "waiting.hitl",
                    "reviewId": review_id,
                    "status": "waiting_hitl",
                },
            )
            _record_terminal_metric("timed_out")
            return

    except asyncio.CancelledError:
        # Arq cancels this task when a SIGTERM's graceful-drain window
        # (WorkerSettings.job_completion_wait, app/worker.py) expires
        # before the job finished. This is the precise counterpart to
        # app/services/reconciliation.py's startup pass — that one cleans
        # up after an *ungraceful* kill (kill -9, OOM) where no Python
        # code got to run at all; this one runs exactly when the process
        # still has a moment to record why, on a graceful but timed-out
        # shutdown. Must re-raise — swallowing CancelledError would break
        # Arq's own shutdown bookkeeping.
        logger.warning("Review %s cancelled — shutdown drain timeout exceeded", review_id)
        review_repo.update_review(
            review_id,
            {
                "status": "failed",
                "status_reason": "interrupted — graceful shutdown drain timeout exceeded",
            },
        )
        await stream_manager.publish(
            review_id,
            {
                "type": "review.failed",
                "reviewId": review_id,
                "status": "failed",
            },
        )
        _record_terminal_metric("cancelled")
        raise
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
        _record_terminal_metric("failed")
