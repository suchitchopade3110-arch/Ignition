"""
Conditional-edge predicates: the deterministic decisions that route the
graph. Pulled out of workflow.py so:
  1. workflow.py stays pure node/edge wiring, readable at a glance
  2. these predicates are unit-testable without instantiating a graph

Three routing decisions matter per the PRD, and all three are enumerable /
deterministic by design — no fuzzy thresholds:
  - hard-rule gate (Agent 1)
  - hallucination retry loop, capped (Agent 3 -> Agent 1)
  - HITL severity gate (Agent 3 -> pause or continue)
"""
from app.config import get_settings
from app.graph.state import ReviewState


def route_after_gate(state: ReviewState) -> str:
    """Agent 1's Hard-Rule Match gate."""
    if state.hard_rule_violation:
        return "direct_rejection"
    return "fan_out"  # parallel Sub-Graphs A, B, C


def route_after_critic(state: ReviewState) -> str:
    """
    Hallucination retry loop with a hard cap — prevents infinite cycles
    and runaway API cost. Cap is a config value, not a magic number.
    """
    settings = get_settings()
    critic_wants_recheck = state.acs_score is None  # placeholder signal; see agent_3_critic.py

    if critic_wants_recheck and state.hallucination_retry_count < settings.hallucination_retry_cap:
        return "retry_context_fetch"

    return "route_hitl"


def route_hitl(state: ReviewState) -> str:
    """
    Deterministic HITL gate: keyed off the structured severity enum the
    Critic outputs, never a subjective confidence score.
    """
    if state.hitl_severity == "critical":
        return "pause_for_human_approval"
    return "finalize_and_post"