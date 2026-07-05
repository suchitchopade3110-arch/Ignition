"""
LangGraph workflow definition: fork -> parallel sub-graphs -> join -> critic.

Pure wiring only. Node logic lives in graph/nodes/, routing decisions live
in graph/routing.py. If you're tempted to add an `if` here, it probably
belongs in routing.py instead.
"""
from langgraph.graph import StateGraph, END

from app.graph.state import ReviewState
from app.graph.routing import route_after_gate, route_after_critic, route_hitl
from app.graph.nodes.agent_1_gate import agent_1_gate
from app.graph.nodes.agent_2a_struct import agent_2a_struct
from app.graph.nodes.agent_2b_chaos import agent_2b_chaos
from app.graph.nodes.agent_2c_security import agent_2c_security
from app.graph.nodes.agent_3_critic import agent_3_critic
from app.graph.nodes.agent_4_autofix import agent_4_autofix


def direct_rejection(state: ReviewState) -> dict:
    return {"final_comment_markdown": f"Rejected: {state.rejection_reason}"}


def pause_for_human_approval(state: ReviewState) -> dict:
    # No-op node — the SSE stream surfaces this state to the dashboard's
    # HITL approval queue; a separate endpoint resumes the graph on approval.
    return {}


def finalize_and_post(state: ReviewState) -> dict:
    from app.services.github_client import GitHubClient

    GitHubClient().post_review_comment(
        repo_full_name=state.repo_full_name,
        pr_number=state.pr_number,
        markdown_body=state.final_comment_markdown or "No findings.",
    )
    return {}


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
        route_after_gate,
        {
            "direct_rejection": "direct_rejection",
            "fan_out": "agent_2a_struct",  # LangGraph fans out via multiple edges below
        },
    )
    # Parallel fan-out: all three read the same post-gate state
    graph.add_edge("agent_1_gate", "agent_2b_chaos")
    graph.add_edge("agent_1_gate", "agent_2c_security")

    # Join at the Critic
    graph.add_edge("agent_2a_struct", "agent_3_critic")
    graph.add_edge("agent_2b_chaos", "agent_3_critic")
    graph.add_edge("agent_2c_security", "agent_3_critic")

    graph.add_conditional_edges(
        "agent_3_critic",
        route_after_critic,
        {
            "retry_context_fetch": "agent_1_gate",  # bounded by hallucination_retry_cap
            "route_hitl": "hitl_check",
        },
    )

    # route_hitl is a second conditional check, kept distinct from the
    # retry-vs-continue decision above for clarity.
    graph.add_conditional_edges(
        "agent_3_critic",
        route_hitl,
        {
            "pause_for_human_approval": "pause_for_human_approval",
            "finalize_and_post": "agent_4_autofix",
        },
    )

    graph.add_edge("agent_4_autofix", "finalize_and_post")
    graph.add_edge("direct_rejection", END)
    graph.add_edge("pause_for_human_approval", END)  # resumed externally on human approval
    graph.add_edge("finalize_and_post", END)

    return graph.compile()