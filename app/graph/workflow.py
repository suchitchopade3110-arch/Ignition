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

    GitHubClient(installation_id=state.installation_id).post_review_comment(
        repo_full_name=state.repo_full_name,
        pr_number=state.pr_number,
        markdown_body=state.final_comment_markdown or "No findings.",
    )
    return {}


def route_after_gate_combined(state: ReviewState) -> list[str]:
    """
    Combined router for Agent 1 gate. If rejected, goes to direct_rejection.
    Otherwise, fans out to the three parallel specialist agents.
    """
    decision = route_after_gate(state)
    if decision == "direct_rejection":
        return ["direct_rejection"]
    return ["agent_2a_struct", "agent_2b_chaos", "agent_2c_security"]


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
    if retry_or_hitl == "retry_context_fetch":
        return "retry_context_fetch"
    return route_hitl(state)


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
            "retry_context_fetch": "agent_1_gate",
            "pause_for_human_approval": "pause_for_human_approval",
            "finalize_and_post": "agent_4_autofix",
        },
    )

    graph.add_edge("agent_4_autofix", "finalize_and_post")
    graph.add_edge("direct_rejection", END)
    graph.add_edge("pause_for_human_approval", END)  # resumed externally on human approval
    graph.add_edge("finalize_and_post", END)

    return graph.compile()