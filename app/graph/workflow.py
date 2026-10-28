"""
LangGraph workflow definition: fork -> parallel sub-graphs -> join -> critic.

Pure wiring only. Node logic lives in graph/nodes/, routing decisions live
in graph/routing.py. If you're tempted to add an `if` here, it probably
belongs in routing.py instead.
"""
import logging
import time

from langgraph.graph import StateGraph, END

from app.graph.state import ReviewState
from app.graph.routing import route_after_gate, route_after_critic, route_hitl
from app.graph.nodes.agent_1_gate import agent_1_gate
from app.graph.nodes.agent_2a_struct import agent_2a_struct
from app.graph.nodes.agent_2b_chaos import agent_2b_chaos
from app.graph.nodes.agent_2c_security import agent_2c_security
from app.graph.nodes.agent_3_critic import agent_3_critic
from app.graph.nodes.agent_4_autofix import agent_4_autofix

logger = logging.getLogger(__name__)


def direct_rejection(state: ReviewState) -> dict:
    """Posts the rejection on the PR through the sticky comment (audit P0-6);
    it used to be stored on the dashboard only, so a hard-rule rejection
    never reached the PR."""
    from app.services.github_client import GitHubClient

    markdown = f"## Ignition Review — rejected\n\n**Hard rule violated:** {state.rejection_reason}"
    gh = GitHubClient(installation_id=state.installation_id)
    if state.head_sha:  # same "check again before posting" rule as finalize_and_post (P1-8)
        current_head = gh.get_pr_head_sha(state.repo_full_name, state.pr_number)
        if current_head and current_head != state.head_sha:
            return {"superseded_by": current_head, "final_comment_markdown": markdown}
    gh.upsert_sticky_comment(
        repo_full_name=state.repo_full_name, pr_number=state.pr_number, body=markdown, bot_login=gh.bot_login,
    )
    return {"final_comment_markdown": markdown}


def pause_for_human_approval(state: ReviewState) -> dict:
    # No-op node — the SSE stream surfaces this state to the dashboard's
    # HITL approval queue; a separate endpoint resumes the graph on approval.
    return {}


# Waits between attempts to post the summary (P2 partial success): three
# attempts in all.
SUMMARY_POST_RETRY_DELAYS = (1.0, 2.0)


def finalize_and_post(state: ReviewState) -> dict:
    from app.services.github_client import GitHubClient

    gh = GitHubClient(installation_id=state.installation_id)
    # Checked again right before posting (audit P1-8): a push during the
    # review makes these results stale, and the sticky comment would
    # overwrite the newer review's.
    if state.head_sha:
        current_head = gh.get_pr_head_sha(state.repo_full_name, state.pr_number)
        if current_head and current_head != state.head_sha:
            logger.info("PR head moved during the review; not posting", extra={
                "repo_full_name": state.repo_full_name, "pr_number": state.pr_number,
            })
            return {"superseded_by": current_head}

    logger.info("Posting final review comment to GitHub", extra={
        "repo_full_name": state.repo_full_name, "pr_number": state.pr_number,
    })
    # Posted before any auto-fix suggestion (P2 partial success). A post
    # that still fails after the retries doesn't fail the review: the
    # pipeline records "comment not posted" and the check run carries the
    # result.
    for attempt, delay in enumerate((*SUMMARY_POST_RETRY_DELAYS, None), start=1):
        try:
            gh.upsert_sticky_comment(
                repo_full_name=state.repo_full_name,
                pr_number=state.pr_number,
                body=state.final_comment_markdown or "No findings.",
                bot_login=gh.bot_login,
            )
            return {"comment_posted": True}
        except Exception:
            logger.warning("Posting the review comment failed (attempt %d)", attempt, exc_info=True)
            if delay is None:
                return {"comment_posted": False}
            time.sleep(delay)
    return {"comment_posted": False}  # unreachable; keeps type checkers happy


def route_after_finalize(state: ReviewState) -> str:
    """Suggestions follow a posted summary, never stand alone (P2)."""
    if state.superseded_by or state.comment_posted is False or not state.enable_auto_fix:
        return END
    return "agent_4_autofix"


def route_after_gate_combined(state: ReviewState) -> list[str]:
    """
    Combined router for Agent 1 gate. If rejected, goes to direct_rejection.
    Otherwise, fans out to the three parallel specialist agents.
    """
    decision = route_after_gate(state)
    if decision == "direct_rejection":
        return ["direct_rejection"]
    # Only the scans the repo has turned on (audit P1-5); none at all goes
    # straight to the Critic.
    return list(state.enabled_agents) or ["agent_3_critic"]


def route_after_critic_combined(state: ReviewState) -> str:
    """
    Single router combining both decisions that follow the Critic:
    1. retry vs. proceed (capped hallucination recheck loop)
    2. pause vs. finalize (deterministic HITL gate)

    Collapsed into one function because LangGraph only supports one
    conditional router per source node — this was previously (incorrectly)
    split across two separate add_conditional_edges calls on the critic,
    the second of which pointed at a node ("hitl_check") that never existed.
    """
    retry_or_hitl = route_after_critic(state)
    if retry_or_hitl == "retry_structural_recheck":
        return "retry_structural_recheck"
    decision = route_hitl(state)
    if decision == "finalize_and_post" and not state.enable_auto_fix:
        return "finalize_without_autofix"  # auto-fix off for this repo (audit P1-5)
    return decision


def build_graph():
    graph = StateGraph(ReviewState)

    graph.add_node("agent_1_gate", agent_1_gate)
    graph.add_node("agent_2a_struct", agent_2a_struct)
    graph.add_node("agent_2b_chaos", agent_2b_chaos)
    graph.add_node("agent_2c_security", agent_2c_security)
    graph.add_node("agent_3_critic", agent_3_critic)
    graph.add_node("agent_4_autofix", agent_4_autofix)
    graph.add_node("direct_rejection", direct_rejection)
    graph.add_node("pause_for_human_approval", pause_for_human_approval)
    graph.add_node("finalize_and_post", finalize_and_post)

    graph.set_entry_point("agent_1_gate")

    graph.add_conditional_edges(
        "agent_1_gate",
        route_after_gate_combined,
        {
            "direct_rejection": "direct_rejection",
            "agent_2a_struct": "agent_2a_struct",
            "agent_2b_chaos": "agent_2b_chaos",
            "agent_2c_security": "agent_2c_security",
            "agent_3_critic": "agent_3_critic",
        },
    )

    # Join at the Critic
    graph.add_edge("agent_2a_struct", "agent_3_critic")
    graph.add_edge("agent_2b_chaos", "agent_3_critic")
    graph.add_edge("agent_2c_security", "agent_3_critic")

    graph.add_conditional_edges(
        "agent_3_critic",
        route_after_critic_combined,
        {
            # Narrow retry: straight back to Agent 2A alone, not through
            # Agent 1's full fan-out — a hallucinated Agent 2A finding
            # doesn't call Agent 2B/2C's already-good findings into
            # question, so re-running them on every retry was pure waste.
            "retry_structural_recheck": "agent_2a_struct",
            "pause_for_human_approval": "pause_for_human_approval",
            # Summary first, suggestions after (P2 partial success):
            # finalize_and_post routes on to agent_4_autofix itself.
            "finalize_and_post": "finalize_and_post",
            "finalize_without_autofix": "finalize_and_post",
        },
    )

    graph.add_conditional_edges("finalize_and_post", route_after_finalize,
                                {"agent_4_autofix": "agent_4_autofix", END: END})
    graph.add_edge("agent_4_autofix", END)
    graph.add_edge("direct_rejection", END)
    graph.add_edge("pause_for_human_approval", END)  # resumed externally on human approval

    return graph.compile()